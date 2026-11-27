import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
import httpx

from app.models.event import FailureRef, RunStat, FailureEvent
from app.security.masking import trim_log, mask_secrets

logger = logging.getLogger(__name__)

class GitHubAdapter:
    key: str = "github"
    config_schema: Dict[str, Any] = {
        "title": "GitHub Actions Configuration",
        "properties": {
            "api_url": {"type": "string", "default": "https://api.github.com", "description": "GitHub API Base URL"},
            "webhook_secret": {"type": "string", "secret": True, "description": "Secret configured in GitHub webhook (HMAC-SHA256)"},
            "access_token": {"type": "string", "secret": True, "description": "Fine-grained token (Actions, Contents, Checks: read)"}
        },
        "required": ["webhook_secret"]
    }

    def verify(self, headers: Dict[str, str], body: bytes, secret: Optional[str]) -> bool:
        """HMAC-SHA256 signature verification against X-Hub-Signature-256."""
        if not secret:
            return True
        hub_signature = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256")
        if not hub_signature or not hub_signature.startswith("sha256="):
            return False
        
        expected_sig = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(hub_signature, expected_sig)

    def parse(self, headers: Dict[str, str], body: bytes) -> Optional[FailureRef | RunStat]:
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse GitHub webhook JSON: {e}")
            return None

        event_name = headers.get("x-github-event") or headers.get("X-GitHub-Event")
        repo_full_name = data.get("repository", {}).get("full_name", "unknown/repo")

        # 1. workflow_run event
        if event_name == "workflow_run":
            run = data.get("workflow_run", {})
            conclusion = run.get("conclusion")
            run_id = str(run.get("id"))

            if conclusion == "success":
                return RunStat(
                    platform=self.key,
                    project=repo_full_name,
                    kind="pipeline",
                    status="success"
                )
            elif conclusion in ["failure", "timed_out"]:
                event_key = f"github:{repo_full_name}:{run_id}:workflow_run"
                return FailureRef(
                    platform=self.key,
                    event_key=event_key,
                    project=repo_full_name,
                    pipeline_id=run_id,
                    job_id="workflow_run",
                    raw_payload=data
                )

        # 2. workflow_job event
        elif event_name == "workflow_job":
            job = data.get("workflow_job", {})
            conclusion = job.get("conclusion")
            run_id = str(job.get("run_id"))
            job_id = str(job.get("id"))

            if conclusion == "success":
                return RunStat(
                    platform=self.key,
                    project=repo_full_name,
                    kind="pipeline",
                    status="success"
                )
            elif conclusion in ["failure", "timed_out"]:
                event_key = f"github:{repo_full_name}:{run_id}:{job_id}"
                return FailureRef(
                    platform=self.key,
                    event_key=event_key,
                    project=repo_full_name,
                    pipeline_id=run_id,
                    job_id=job_id,
                    raw_payload=data
                )

        # 3. pull_request event (merged)
        elif event_name == "pull_request":
            pr = data.get("pull_request", {})
            if data.get("action") == "closed" and pr.get("merged") is True:
                return RunStat(
                    platform=self.key,
                    project=repo_full_name,
                    kind="merge",
                    status="merged"
                )

        return None

    def collect(self, ref: FailureRef, creds: Dict[str, Any]) -> FailureEvent:
        payload = ref.raw_payload
        run = payload.get("workflow_run") or {}
        job = payload.get("workflow_job") or {}
        
        # Commit details
        head_commit = run.get("head_commit") or payload.get("head_commit") or {}
        commit_sha = head_commit.get("id") or run.get("head_sha") or "unknown_sha"
        commit_message = head_commit.get("message") or "No commit message"
        author_info = head_commit.get("author") or {}
        author_name = author_info.get("name") or "Unknown Author"
        author_email = author_info.get("email") or "unknown@example.com"

        job_name = job.get("name") or run.get("name") or "build_workflow"
        
        # Determine failed step name if present
        failed_step = None
        for step in job.get("steps", []):
            if step.get("conclusion") == "failure":
                failed_step = step.get("name")
                break
        
        stage = f"{job_name} / {failed_step}" if failed_step else job_name
        conclusion = job.get("conclusion") or run.get("conclusion") or "failure"
        ref_branch = run.get("head_branch") or "main"
        html_url = job.get("html_url") or run.get("html_url") or ""

        # Fetch logs if needed or extract from payload
        raw_log = payload.get("log") or ""
        token = creds.get("access_token")
        api_url = creds.get("api_url", "https://api.github.com")

        if not raw_log and token and ref.job_id != "workflow_run" and ref.job_id.isdigit():
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(
                        f"{api_url}/repos/{ref.project}/actions/jobs/{ref.job_id}/logs",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
                    )
                    if resp.status_code == 200:
                        raw_log = resp.text
            except Exception as e:
                logger.warning(f"Failed to fetch GitHub job log via API: {e}")

        sanitized_log = mask_secrets(trim_log(raw_log))

        return FailureEvent(
            event_key=ref.event_key,
            platform=self.key,
            project=ref.project,
            branch=ref_branch,
            pipeline_id=ref.pipeline_id,
            url=html_url,
            job_id=ref.job_id,
            job_name=job_name,
            stage=stage,
            environment=None,
            failure_reason=conclusion,
            log_excerpt=sanitized_log,
            commit_sha=commit_sha,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            changed_files=[],
            change_request=str(run.get("pull_requests", [{}])[0].get("number", "") if run.get("pull_requests") else ""),
            urls={"workflow_run": html_url},
            timestamps={"finished_at": None}
        )
