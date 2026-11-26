from typing import Protocol, Optional, Dict, Any
from pydantic import BaseModel

class ExternalRef(BaseModel):
    task_id: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = {}

class Connector(Protocol):
    """
    Protocol for output notification and issue tracking connectors.
    Kanvaro (MCP), Slack (REST), Jira (REST), and Email all implement this.
    """
    type: str # 'mcp' | 'rest' | 'email'

    def create_task(self, issue: Any) -> ExternalRef:
        """Create a task in the external project tracking system."""
        ...

    def assign(self, ref: ExternalRef, user_identifier: str) -> None:
        """Assign the external task to a specific user."""
        ...

    def update_status(self, ref: ExternalRef, status: str) -> None:
        """Sync issue status changes (Open, In Progress, Resolved, Won't Fix)."""
        ...

    def comment(self, ref: ExternalRef, text: str) -> None:
        """Post a comment or update to the external task."""
        ...

    def notify(self, user_identifier: str, summary: str, link: str) -> None:
        """Direct notification (e.g. Email, Slack message)."""
        ...
