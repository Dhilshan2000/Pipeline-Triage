import logging
from datetime import datetime
from typing import Dict, Any
from redis import Redis
from rq import Worker, Queue, Connection

from app.config import settings
from app.database import get_sync_db
from app.adapters.registry import adapter_registry
from app.models.event import FailureRef, FailureEvent
from app.sonarqube.client import sonarqube_client
from app.classifier.engine import classify_failure
from app.router.engine import route_owner
from app.deduplication.fingerprint import create_or_update_issue_atomic
from app.report.generator import generate_triage_report
from app.connectors.kanvaro_mcp import KanvaroMCPConnector
from app.connectors.outbox import enqueue_outbox_notification, process_outbox_queue
from app.rag.knowledge_base import knowledge_base
from app.security.crypto import decrypt_credential

logger = logging.getLogger(__name__)

listen = ['default', 'failures', 'notifications']

def process_failure_job(delivery_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 8-step pipeline for an incoming failure:
    1. Adapter builds FailureEvent
    2. Trim + secret mask
    3. SonarQube query (if applicable)
    4. 8-category classification (Rules -> Claude -> Needs review)
    5. Safe owner routing (Rules + Git email)
    6. Duplicate check & atomic issue upsert
    7. Grounded RAG + Claude report generation (JSON)
    8. Outbox notifications (Email + Kanvaro MCP task)
    """
    db = get_sync_db()
    event_key = delivery_data.get("event_key")
    platform = delivery_data.get("platform", "gitlab")
    logger.info(f"[Step 2] Processing failure pipeline for {event_key} ({platform})")

    # Step 2: Adapter collect FailureEvent
    adapter = adapter_registry.get(platform)
    if not adapter:
        logger.error(f"Adapter not found for platform: {platform}")
        return {"status": "error", "message": f"Unknown platform {platform}"}

    ref = FailureRef(
        platform=platform,
        event_key=event_key,
        project=delivery_data.get("project", "unknown"),
        pipeline_id=str(delivery_data.get("pipeline_id", "0")),
        job_id=str(delivery_data.get("job_id", "0")),
        raw_payload=delivery_data.get("raw_payload", {})
    )

    # Fetch credentials for adapter
    creds = {}
    try:
        adapter_doc = db.adapter_settings.find_one({"key": platform})
        if adapter_doc:
            creds = dict(adapter_doc.get("config", {}))
            for k, enc_v in adapter_doc.get("encrypted_credentials", {}).items():
                if enc_v:
                    try:
                        creds[k] = decrypt_credential(enc_v)
                    except Exception:
                        creds[k] = enc_v
    except Exception as e:
        logger.warning(f"Failed to load adapter settings for {platform}: {e}")

    # Fallback to settings if not found in db
    if platform == "gitlab" and not creds.get("access_token"):
        creds["access_token"] = getattr(settings, "GITLAB_API_TOKEN", None)
    elif platform == "github" and not creds.get("access_token"):
        creds["access_token"] = getattr(settings, "GITHUB_API_TOKEN", None)

    # Collect facts (includes Step 3: log trimming and secret masking)
    event: FailureEvent = adapter.collect(ref, creds=creds)

    # Step 4: SonarQube query
    sonar_data = None
    if "sonar" in event.job_name.lower() or "sonar" in (event.stage or "").lower():
        logger.info(f"[Step 4] Checking SonarQube quality gate for project: {event.project}")
        finding = sonarqube_client.get_project_quality_gate(event.project)
        if finding:
            sonar_data = finding.model_dump()

    # Step 5: Classify into the 8 categories
    category, confidence, evidence, source = classify_failure(event, mode="hybrid")
    logger.info(f"[Step 5] Classified as '{category}' (conf: {confidence:.2f}, source: {source})")

    # Store failure record in failures collection (Step 1 output)
    failure_doc = {
        "event_key": event.event_key,
        "platform": event.platform,
        "pipeline_id": event.pipeline_id,
        "job_id": event.job_id,
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
        "classifier_source": source,
        "masked_event": event.model_dump(),
        "created_at": datetime.utcnow()
    }
    try:
        db.failures.update_one({"event_key": event.event_key}, {"$set": failure_doc}, upsert=True)
    except Exception as e:
        logger.warning(f"Failed to upsert failure doc: {e}")

    # Step 6: Route owner
    assignee_email, routing_reason = route_owner(category, confidence, event)
    logger.info(f"[Step 6] Routed to: {assignee_email} ({routing_reason})")

    # Step 7: Duplicate check (fingerprint atomic merge / create)
    issue_doc, is_new = create_or_update_issue_atomic(
        db=db,
        event=event,
        category=category,
        confidence=confidence,
        evidence=evidence,
        source=source,
        assignee=assignee_email
    )
    issue_id = str(issue_doc["_id"])
    logger.info(f"[Step 7] Issue {issue_id}: is_new={is_new}, occurrences={issue_doc.get('occurrence_count')}")

    # Step 8: Write detailed report (RAG + Claude)
    report = generate_triage_report(event, category, sonar_data)
    db.issues.update_one(
        {"_id": issue_doc["_id"]},
        {"$set": {"report": report.model_dump()}}
    )

    # Step 9: Notify via enabled connectors if this is a new issue
    if is_new:
        issue_link = f"{settings.NEXT_PUBLIC_API_URL.replace(':8000', ':3000')}/issues/{issue_id}"
        notification_summary = f"{report.summary}\nCategory: {category} | Effort: {report.effort_estimate}"

        # 9a. Enqueue Email notification
        enqueue_outbox_notification(
            db=db,
            issue_id=issue_id,
            connector_type="email",
            payload={
                "recipient": assignee_email,
                "summary": notification_summary,
                "link": issue_link
            }
        )

        # 9b. Enqueue Kanvaro MCP task creation
        enqueue_outbox_notification(
            db=db,
            issue_id=issue_id,
            connector_type="kanvaro",
            payload={
                "issue": {
                    "_id": issue_id,
                    "title": issue_doc["title"],
                    "category": category,
                    "project": event.project,
                    "branch": event.branch,
                    "assignee": assignee_email,
                    "fingerprint": issue_doc["fingerprint"]
                }
            }
        )

        # 9c. Enqueue any enabled REST connectors configured in Settings (e.g. Slack, Jira)
        for conn in db.connector_settings.find({"enabled": True, "type": "rest"}):
            conn_cfg = dict(conn.get("config", {}))
            for k, enc_v in conn.get("encrypted_credentials", {}).items():
                if enc_v:
                    try:
                        conn_cfg[k] = decrypt_credential(enc_v)
                    except Exception:
                        conn_cfg[k] = enc_v
            enqueue_outbox_notification(
                db=db,
                issue_id=issue_id,
                connector_type="slack",
                payload={
                    "recipient": assignee_email,
                    "summary": notification_summary,
                    "link": issue_link,
                    "config": conn_cfg
                }
            )

        # Trigger immediate outbox send
        try:
            process_outbox_queue()
        except Exception as e:
            logger.warning(f"Immediate outbox processing error (will be retried): {e}")

    return {
        "status": "success",
        "issue_id": issue_id,
        "is_new": is_new,
        "category": category,
        "assignee": assignee_email
    }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Connecting RQ Worker to Redis at {settings.REDIS_URL}...")
    # Initialize Qdrant seed knowledge chunks on startup
    try:
        knowledge_base.seed_knowledge()
    except Exception as e:
        logger.warning(f"Knowledge base init warning: {e}")

    redis_conn = Redis.from_url(settings.REDIS_URL)
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen))
        logger.info("Pipeline Triage Worker started. Listening for background jobs...")
        worker.work()
