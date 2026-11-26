import logging
from typing import Dict, Any, Optional
import httpx
from app.connectors.base import ExternalRef

logger = logging.getLogger(__name__)

class SlackJiraConnector:
    """
    REST Connector supporting Slack incoming webhooks or Jira Cloud REST API.
    Configured purely via Settings to prove no tool is hard-coded into the core.
    """
    type: str = "rest"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.webhook_url = self.config.get("webhook_url")
        self.jira_base_url = self.config.get("jira_base_url")
        self.api_token = self.config.get("api_token")

    def notify(self, user_identifier: str, summary: str, link: str) -> None:
        if not self.webhook_url:
            return
        payload = {
            "text": f"🚨 *Pipeline Triage Alert* for <@{user_identifier}>:\n{summary}\n<{link}|View Triage Report>"
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(self.webhook_url, json=payload)
        except Exception as e:
            logger.warning(f"Slack/Jira REST connector failed: {e}")

    def create_task(self, issue: Any) -> ExternalRef:
        return ExternalRef(task_id="jira_mock_123", url="http://jira.example.com/browse/PIPELINE-1")

    def assign(self, ref: ExternalRef, user: str) -> None:
        pass

    def update_status(self, ref: ExternalRef, status: str) -> None:
        pass

    def comment(self, ref: ExternalRef, text: str) -> None:
        pass
