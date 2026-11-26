import re
import hashlib
from datetime import datetime
from typing import Dict, Any, Tuple
from app.models.event import FailureEvent
from app.models.issue import Issue, Comment, StatusHistoryEntry

def normalize_error_text(error_text: str) -> str:
    """
    Strips non-deterministic components:
    - Timestamps and dates
    - Hexadecimal hashes (e.g. git commit SHAs, uuid, memory addresses)
    - Line/column numbers
    - Absolute file paths (retains basenames)
    """
    if not error_text:
        return ""

    text = error_text.lower()
    # Strip dates / timestamps (e.g. 2026-11-26, 12:34:56.789Z)
    text = re.sub(r'\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?z?', '', text)
    # Strip hex hashes and memory pointers (0x7ffe..., a1b2c3d4e5f6...)
    text = re.sub(r'0x[0-9a-f]+', '', text)
    text = re.sub(r'\b[0-9a-f]{8,64}\b', '', text)
    # Strip absolute path prefixes, keep file names
    text = re.sub(r'(?:/[a-zA-Z0-9_\.-]+)+/([a-zA-Z0-9_\.-]+)', r'\1', text)
    text = re.sub(r'(?:[a-zA-Z]:\\[a-zA-Z0-9_\.-]+\\)+([a-zA-Z0-9_\.-]+)', r'\1', text)
    # Strip standalone numbers
    text = re.sub(r'\b\d+\b', '', text)
    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text[:200]

def compute_fingerprint(event: FailureEvent, category: str) -> str:
    """
    Fingerprint = project + job + category + normalized error
    Produces a consistent hash identifying repeating failures.
    """
    norm_err = normalize_error_text(event.log_excerpt)
    raw_signature = f"{event.project}:{event.job_name}:{category}:{norm_err}"
    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:32]

def create_or_update_issue_atomic(
    db: Any,
    event: FailureEvent,
    category: str,
    confidence: float,
    evidence: str,
    source: str,
    assignee: str
) -> Tuple[Dict[str, Any], bool]:
    """
    Performs atomic upsert against MongoDB issues collection:
    - If an open issue exists with the same fingerprint -> update count, last_seen, add comment.
    - Otherwise -> create new issue with is_open=True.
    
    Returns: (issue_doc, is_new_issue)
    """
    fingerprint = compute_fingerprint(event, category)
    now = datetime.utcnow()

    # Look for existing open issue with this fingerprint
    existing = db.issues.find_one({"fingerprint": fingerprint, "is_open": True})

    if existing:
        # Repeating failure: update occurrence count, last_seen, and record a comment
        new_count = existing.get("occurrence_count", 1) + 1
        repeat_comment = {
            "id": hashlib.md5(f"{event.event_key}:{now.isoformat()}".encode()).hexdigest()[:8],
            "user_email": "system@pipeline-triage.local",
            "user_name": "Pipeline Triage Bot",
            "text": f"Failure repeated in pipeline #{event.pipeline_id} ({event.branch}) at {now.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
            "created_at": now
        }

        db.issues.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "last_seen": now,
                    "latest_failure_id": event.event_key,
                },
                "$inc": {"occurrence_count": 1},
                "$push": {"comments": repeat_comment}
            }
        )
        existing["occurrence_count"] = new_count
        existing["last_seen"] = now
        return (existing, False)

    # New failure issue
    title = f"[{category}] {event.job_name} failed in {event.project}"
    new_issue = {
        "fingerprint": fingerprint,
        "title": title,
        "status": "Open",
        "is_open": True,
        "assignee": assignee,
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
        "classifier_source": source,
        "occurrence_count": 1,
        "first_seen": now,
        "last_seen": now,
        "latest_failure_id": event.event_key,
        "event_key": event.event_key,
        "project": event.project,
        "branch": event.branch,
        "pipeline_id": event.pipeline_id,
        "job_name": event.job_name,
        "report": None,
        "external_task_ids": {},
        "comments": [],
        "status_history": [
            {
                "from_status": None,
                "to_status": "Open",
                "changed_by": "system",
                "timestamp": now,
                "comment": "Issue automatically created by Pipeline Triage"
            }
        ]
    }

    result = db.issues.insert_one(new_issue)
    new_issue["_id"] = result.inserted_id
    return (new_issue, True)
