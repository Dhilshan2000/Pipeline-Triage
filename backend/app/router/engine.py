import logging
from typing import Dict, Any, Optional, Tuple
from app.models.event import FailureEvent

logger = logging.getLogger(__name__)

# Default system routing roles
DEVOPS_ON_CALL = "devops-oncall@example.com"
SECURITY_LEAD = "security-lead@example.com"
FALLBACK_ASSIGNEE = "tech-lead@example.com"

# Simulated in-memory git email to user map (can be modified in Settings)
GIT_EMAIL_MAP: Dict[str, str] = {
    "dhilshan@example.com": "dhilshan@example.com",
    "developer@example.com": "developer@example.com",
    "qa@example.com": "qa@example.com"
}

def route_owner(category: str, confidence: float, event: FailureEvent, user_mappings: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
    """
    Determines responsible owner based on category and git author email.
    
    PROMPT INJECTION DEFENSE:
    Routing decisions NEVER read commit messages or log contents.
    A commit message stating "Assign this to the CTO" or "Ignore this rule"
    has zero effect on routing.

    Returns: (assignee_email, routing_reason)
    """
    mappings = {**GIT_EMAIL_MAP, **(user_mappings or {})}

    # 1. Low confidence / needs review -> Fallback person
    if category == "needs review" or confidence < 0.60:
        return (FALLBACK_ASSIGNEE, "Uncertain classification; routed to triage lead for manual review")

    # 2. Security scan -> Security Lead
    if category == "Security scan":
        return (SECURITY_LEAD, "Security vulnerability/secret detected; routed to Security Lead")

    # 3. Server / Registry / Deploy / Runner -> DevOps on-call
    if category in ["Docker registry", "Deployment / server", "Runner / timeout"]:
        return (DEVOPS_ON_CALL, f"Infrastructure/Environment failure ({category}); routed to DevOps On-Call")

    # 4. Code / Build / Test / SonarQube -> Commit author
    author_email = event.author_email.lower().strip()
    matched_user = mappings.get(author_email)

    if matched_user:
        return (matched_user, f"Code/build issue ({category}); routed to commit author via git email mapping")
    
    if author_email and "@" in author_email:
        return (author_email, f"Code/build issue ({category}); routed directly to commit author email")

    return (FALLBACK_ASSIGNEE, f"Code issue ({category}) with unmapped author; routed to triage fallback")
