import logging
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

class QualityGateCondition(BaseModel):
    metric: str
    status: str # 'ERROR' or 'OK'
    actual_value: Optional[str] = None
    error_threshold: Optional[str] = None
    comparator: Optional[str] = None

class SonarFinding(BaseModel):
    project_key: str
    status: str # 'ERROR' or 'OK'
    failing_conditions: List[QualityGateCondition] = []
    affected_files: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

class SonarQubeClient:
    """
    Read-only client for SonarQube Web API using triage-bot user token (Browse permission).
    Never writes or modifies quality gate or analysis rules.
    """
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or settings.SONARQUBE_URL).rstrip("/")
        self.token = token or settings.SONARQUBE_TRIAGE_BOT_TOKEN

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {}
        if self.token:
            # SonarQube basic auth uses token as username with empty password
            import base64
            auth_str = f"{self.token}:"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {b64_auth}"
        return headers

    def get_project_quality_gate(self, project_key: str) -> Optional[SonarFinding]:
        """Fetches failing conditions from api/qualitygates/project_status."""
        url = f"{self.base_url}/api/qualitygates/project_status"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    url,
                    params={"projectKey": project_key},
                    headers=self._get_auth_headers()
                )
                if resp.status_code != 200:
                    logger.warning(f"SonarQube returned status {resp.status_code} for project {project_key}")
                    return None

                data = resp.json().get("projectStatus", {})
                status = data.get("status", "OK")
                
                failing_conditions: List[QualityGateCondition] = []
                for cond in data.get("conditions", []):
                    if cond.get("status") == "ERROR":
                        failing_conditions.append(
                            QualityGateCondition(
                                metric=cond.get("metricKey", "unknown_metric"),
                                status="ERROR",
                                actual_value=cond.get("actualValue"),
                                error_threshold=cond.get("errorThreshold"),
                                comparator=cond.get("comparator")
                            )
                        )

                # Fetch recent unresolved issues for line numbers and authors
                issues = self.get_recent_issues(project_key)

                return SonarFinding(
                    project_key=project_key,
                    status=status,
                    failing_conditions=failing_conditions,
                    issues=issues
                )
        except Exception as e:
            logger.error(f"Error connecting to SonarQube at {url}: {e}")
            return None

    def get_recent_issues(self, project_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Queries api/issues/search to find exact files, lines, and blamed authors."""
        url = f"{self.base_url}/api/issues/search"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    url,
                    params={
                        "componentKeys": project_key,
                        "resolved": "false",
                        "ps": limit
                    },
                    headers=self._get_auth_headers()
                )
                if resp.status_code != 200:
                    return []
                
                raw_issues = resp.json().get("issues", [])
                parsed_issues = []
                for issue in raw_issues:
                    parsed_issues.append({
                        "key": issue.get("key"),
                        "rule": issue.get("rule"),
                        "severity": issue.get("severity"),
                        "component": issue.get("component"),
                        "line": issue.get("line"),
                        "message": issue.get("message"),
                        "author": issue.get("author")
                    })
                return parsed_issues
        except Exception as e:
            logger.warning(f"Could not retrieve SonarQube issues: {e}")
            return []

sonarqube_client = SonarQubeClient()
