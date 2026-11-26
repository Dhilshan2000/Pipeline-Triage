import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.database import get_sync_db
from app.connectors.email import EmailConnector
from app.connectors.kanvaro_mcp import KanvaroMCPConnector
from app.connectors.slack_jira import SlackJiraConnector

logger = logging.getLogger(__name__)

# Retry backoff delays: 10 seconds, 30 seconds, 2 minutes
RETRY_BACKOFF_SECONDS = [10, 30, 120]

def enqueue_outbox_notification(db: Any, issue_id: str, connector_type: str, payload: Dict[str, Any]):
    """Stores outgoing notification in MongoDB outbox collection with retry metadata."""
    now = datetime.utcnow()
    outbox_doc = {
        "issue_id": str(issue_id),
        "connector_type": connector_type,
        "payload": payload,
        "state": "pending", # 'pending', 'sent', 'failed'
        "attempts": 0,
        "max_attempts": 3,
        "next_try": now,
        "created_at": now,
        "last_error": None
    }
    db.notification_outbox.insert_one(outbox_doc)
    logger.info(f"Enqueued {connector_type} notification in outbox for issue {issue_id}")

def process_outbox_queue():
    """
    Worker scheduled job that executes pending notifications and retries
    transient connection failures with backoff.
    """
    db = get_sync_db()
    now = datetime.utcnow()
    pending_items = list(db.notification_outbox.find({
        "state": "pending",
        "next_try": {"$lte": now}
    }))

    for item in pending_items:
        item_id = item["_id"]
        connector_type = item["connector_type"]
        payload = item["payload"]
        attempts = item.get("attempts", 0) + 1

        try:
            if connector_type == "email":
                connector = EmailConnector()
                connector.notify(
                    user_email=payload["recipient"],
                    summary=payload["summary"],
                    link=payload["link"]
                )
            elif connector_type == "kanvaro":
                kanvaro = KanvaroMCPConnector()
                kanvaro.create_task(payload.get("issue", {}))
            elif connector_type == "slack":
                slack = SlackJiraConnector(config=payload.get("config", {}))
                slack.notify(
                    user_identifier=payload["recipient"],
                    summary=payload["summary"],
                    link=payload["link"]
                )

            # Mark sent
            db.notification_outbox.update_one(
                {"_id": item_id},
                {"$set": {"state": "sent", "sent_at": datetime.utcnow(), "attempts": attempts}}
            )
            logger.info(f"Successfully processed outbox item {item_id} ({connector_type})")

        except Exception as e:
            logger.warning(f"Error delivering outbox item {item_id} ({connector_type}): {e}")
            if attempts >= item.get("max_attempts", 3):
                db.notification_outbox.update_one(
                    {"_id": item_id},
                    {"$set": {"state": "failed", "last_error": str(e), "attempts": attempts}}
                )
            else:
                delay = RETRY_BACKOFF_SECONDS[min(attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
                next_try = datetime.utcnow() + timedelta(seconds=delay)
                db.notification_outbox.update_one(
                    {"_id": item_id},
                    {"$set": {"next_try": next_try, "last_error": str(e), "attempts": attempts}}
                )
