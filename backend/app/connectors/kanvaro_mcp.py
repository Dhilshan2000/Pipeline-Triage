import logging
import datetime
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.connectors.base import ExternalRef

logger = logging.getLogger(__name__)

class KanvaroMCPConnector:
    """
    Kanvaro Connector connecting to mock or production Kanvaro server.
    Manages bot session token with 7-day automatic renewal.
    """
    type: str = "mcp"

    def __init__(self, base_url: Optional[str] = None, bot_user: Optional[str] = None, bot_password: Optional[str] = None):
        # Kanvaro URL without SSE suffix for REST/HTTP API endpoints
        raw_url = base_url or settings.KANVARO_MCP_URL
        self.base_url = raw_url.replace("/sse", "").rstrip("/")
        self.bot_user = bot_user or settings.KANVARO_BOT_USER
        self.bot_password = bot_password or settings.KANVARO_BOT_PASSWORD
        self._session_token: Optional[str] = None
        self._token_expiry: Optional[datetime.datetime] = None

    def _ensure_session(self) -> str:
        """Logs into Kanvaro if session is missing or expiring within 1 hour."""
        now = datetime.datetime.utcnow()
        if self._session_token and self._token_expiry and self._token_expiry > (now + datetime.timedelta(hours=1)):
            return self._session_token

        logger.info(f"Authenticating bot user '{self.bot_user}' with Kanvaro at {self.base_url}...")
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/auth/login",
                    json={"username": self.bot_user, "password": self.bot_password}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._session_token = data.get("token")
                    days = data.get("expires_in_days", 7)
                    self._token_expiry = now + datetime.timedelta(days=days)
                    logger.info("Successfully established 7-day Kanvaro bot session.")
                    return self._session_token
                else:
                    raise RuntimeError(f"Kanvaro login returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Kanvaro authentication failed: {e}")
            raise e

    def _headers(self) -> Dict[str, str]:
        token = self._ensure_session()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def create_task(self, issue: Dict[str, Any]) -> ExternalRef:
        """Creates a task in Kanvaro assigned to the issue owner."""
        token = self._ensure_session()
        url = f"{self.base_url}/tasks"
        payload = {
            "title": issue.get("title", "CI Build Failure"),
            "description": (
                f"Automated Triage Task\n\n"
                f"Category: {issue.get('category')}\n"
                f"Project: {issue.get('project')}\n"
                f"Branch: {issue.get('branch')}\n"
                f"Fingerprint: {issue.get('fingerprint')}\n"
            ),
            "assignee": issue.get("assignee"),
            "priority": "High" if issue.get("category") in ["Security scan", "Deployment / server"] else "Normal",
            "metadata": {"issue_id": str(issue.get("_id", "")), "fingerprint": issue.get("fingerprint")}
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=self._headers())
            if resp.status_code in [200, 201]:
                data = resp.json()
                task_id = data.get("task_id")
                task_url = data.get("url")
                return ExternalRef(task_id=task_id, url=task_url, metadata=data)
            else:
                raise RuntimeError(f"Kanvaro create_task failed: {resp.status_code} {resp.text}")

    def update_status(self, ref: ExternalRef, status: str) -> None:
        """Syncs issue status to Kanvaro (e.g. Open -> In Progress -> Resolved)."""
        if not ref.task_id or ref.task_id == "email_only":
            return
        url = f"{self.base_url}/tasks/{ref.task_id}/status"
        with httpx.Client(timeout=10.0) as client:
            resp = client.patch(url, json={"status": status}, headers=self._headers())
            if resp.status_code != 200:
                logger.warning(f"Kanvaro status update returned {resp.status_code}")

    def comment(self, ref: ExternalRef, text: str) -> None:
        """Adds a comment to the Kanvaro task."""
        if not ref.task_id or ref.task_id == "email_only":
            return
        url = f"{self.base_url}/tasks/{ref.task_id}/status"
        with httpx.Client(timeout=10.0) as client:
            client.patch(url, json={"status": "IN_PROGRESS", "comment": text}, headers=self._headers())

    def assign(self, ref: ExternalRef, user_identifier: str) -> None:
        pass

    def notify(self, user_identifier: str, summary: str, link: str) -> None:
        pass
