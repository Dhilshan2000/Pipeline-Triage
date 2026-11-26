import logging
import datetime
from typing import Dict, Any, List
from app.database import get_sync_db
from app.deduplication.fingerprint import normalize_error_text
from app.llm.provider import llm_provider

logger = logging.getLogger(__name__)

PERMANENT_FIX_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause": {"type": "string"},
        "permanent_fix": {"type": "string"},
        "effort_estimate": {"type": "string"},
        "owner_role": {"type": "string"}
    },
    "required": ["root_cause", "permanent_fix", "effort_estimate", "owner_role"],
    "additionalProperties": False
}

def generate_pattern_signature(failure: Dict[str, Any]) -> str:
    """
    Signature = category + failed job + normalized error text
    """
    cat = failure.get("category", "General")
    event = failure.get("masked_event", {})
    job = event.get("job_name", "job")
    log = event.get("log_excerpt", "")
    norm_err = normalize_error_text(log)[:120]
    return f"{cat}::{job}::{norm_err}"

def detect_recurring_patterns():
    """
    Scheduled job: scans failures in the past 30 days.
    If 3 or more occurrences share the same signature, groups them into a pattern
    and asks Claude for a permanent infrastructural fix.
    """
    db = get_sync_db()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    
    failures = list(db.failures.find({"created_at": {"$gte": cutoff}}))
    if not failures:
        return []

    # Group by signature
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for f in failures:
        sig = generate_pattern_signature(f)
        groups.setdefault(sig, []).append(f)

    detected_patterns = []
    for sig, occurrences in groups.items():
        if len(occurrences) >= 3:
            first_seen = min(o.get("created_at", datetime.datetime.utcnow()) for o in occurrences)
            last_seen = max(o.get("created_at", datetime.datetime.utcnow()) for o in occurrences)
            sample = occurrences[0]
            cat = sample.get("category", "General")
            job_name = sample.get("masked_event", {}).get("job_name", "job")
            affected_projects = list(set(o.get("masked_event", {}).get("project", "unknown") for o in occurrences))

            # Query Claude for permanent fix
            system_prompt = (
                "You are an experienced Site Reliability Engineer.\n"
                "Multiple CI/CD build failures have formed a recurring pattern over 30 days.\n"
                "Propose a permanent structural fix to eradicate this recurring issue."
            )
            user_prompt = (
                f"Pattern Signature: {sig}\n"
                f"Category: {cat}\n"
                f"Failed Job: {job_name}\n"
                f"Occurrences: {len(occurrences)} times in last 30 days\n"
                f"Affected Projects: {affected_projects}\n"
                f"Sample Error Excerpt: {sample.get('masked_event', {}).get('log_excerpt', '')[:1000]}\n"
            )

            try:
                fix_proposal = llm_provider.complete_structured(system_prompt, user_prompt, PERMANENT_FIX_SCHEMA)
            except Exception as e:
                logger.warning(f"Claude pattern fix generation error: {e}")
                fix_proposal = {
                    "root_cause": f"Repeated {cat} in job '{job_name}' across {len(affected_projects)} projects.",
                    "permanent_fix": "Investigate environment configuration drift and introduce automated pre-merge checks.",
                    "effort_estimate": "1-2 days",
                    "owner_role": "DevOps on-call" if "server" in cat.lower() or "docker" in cat.lower() else "Lead Developer"
                }

            pattern_doc = {
                "signature": sig,
                "category": cat,
                "job_name": job_name,
                "count": len(occurrences),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "affected_projects": affected_projects,
                "suggested_fix": fix_proposal,
                "status": "Active", # 'Active' or 'Resolved'
                "updated_at": datetime.datetime.utcnow()
            }

            db.patterns.update_one(
                {"signature": sig},
                {"$set": pattern_doc},
                upsert=True
            )
            detected_patterns.append(pattern_doc)

    logger.info(f"Pattern detection completed: {len(detected_patterns)} recurring patterns identified.")
    return detected_patterns
