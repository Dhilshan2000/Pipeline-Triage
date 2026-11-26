import hmac
import json
import logging
from typing import Dict, Any, Optional
import httpx

from app.models.event import FailureRef, RunStat, FailureEvent
from app.security.masking import trim_log, mask_secrets

logger = logging.getLogger(__name__)

class GitLabAdapter:
    key: str = "gitlab"
    config_schema: Dict[str, Any] = {
        "title": "GitLab CI Configuration",
        "properties": {
            "api_url": {"type": "string", "default": "https://gitlab.com/api/v4", "description": "GitLab API Base URL"},
            "webhook_secret": {"type": "string", "secret": True, "description": "Secret token configured in GitLab webhook"},
            "access_token": {"type": "string", "secret": True, "description": "Project access token (read_api)"}
        },
        "required": ["webhook_secret"]
    }

    def verify(self, headers: Dict[str, str], body: bytes, secret: Optional[str]) -> bool:
        """Constant-time comparison of X-Gitlab-Token header."""
        if not secret:
            return True
        header_token = headers.get("x-gitlab-token") or headers.get("X-Gitlab-Token")
        if not header_token:
            return False
        return hmac.compare_digest(header_token, secret)

    def parse(self, headers: Dict[str, str], body: bytes) -> Optional[FailureRef | RunStat]:
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse GitLab webhook JSON: {e}")
            return None

        object_kind = data.get("object_kind")

        # 1. Pipeline Webhook
        if object_kind == "pipeline":
            attrs = data.get("object_attributes", {})
            status = attrs.get("status")
            project_path = data.get("project", {}).get("path_with_namespace", "unknown/project")
            pipeline_id = str(attrs.get("id"))

            if status == "success":
                return RunStat(
                    platform=self.key,
                    project=project_path,
                    kind="pipeline",
                    status="success",
                    environment=attrs.get("environment")
                )
            elif status == "failed":
                # Find failed build/job in builds array
                builds = data.get("builds", [])
                failed_build = next((b for b in builds if b.get("status") == "failed"), {})
                job_id = str(failed_build.get("id", "pipeline_failed"))
                event_key = f"gitlab:{project_path}:{pipeline_id}:{job_id}"
                return FailureRef(
                    platform=self.key,
                    event_key=event_key,
                    project=project_path,
                    pipeline_id=pipeline_id,
                    job_id=job_id,
                    raw_payload=data
                )

        # 2. Job / Build Webhook
        elif object_kind == "build":
            build_status = data.get("build_status")
            project_path = data.get("repository", {}).get("name") or data.get("project_name", "unknown/project")
            pipeline_id = str(data.get("pipeline_id"))
            job_id = str(data.get("build_id"))

            if build_status == "success":
                return RunStat(
                    platform=self.key,
                    project=project_path,
                    kind="pipeline",
                    status="success"
                )
            elif build_status == "failed":
                event_key = f"gitlab:{project_path}:{pipeline_id}:{job_id}"
                return FailureRef(
                    platform=self.key,
                    event_key=event_key,
                    project=project_path,
                    pipeline_id=pipeline_id,
                    job_id=job_id,
                    raw_payload=data
                )

        # 3. Merge Request Webhook
        elif object_kind == "merge_request":
            attrs = data.get("object_attributes", {})
            if attrs.get("action") == "merge" or attrs.get("state") == "merged":
                project_path = data.get("project", {}).get("path_with_namespace", "unknown/project")
                return RunStat(
                    platform=self.key,
                    project=project_path,
                    kind="merge",
                    status="merged"
                )

        return None

    def collect(self, ref: FailureRef, creds: Dict[str, Any]) -> FailureEvent:
        """Collect facts via read-only API calls or enriched webhook payload."""
        payload = ref.raw_payload
        attrs = payload.get("object_attributes", {})
        commit_info = payload.get("commit", {}) or attrs.get("commit", {})
        project_name = ref.project

        # Extract commit facts
        commit_sha = commit_info.get("id") or commit_info.get("sha") or "unknown_sha"
        commit_message = commit_info.get("message") or "No commit message"
        author_info = commit_info.get("author", {})
        author_name = author_info.get("name") or commit_info.get("author_name") or "Unknown Author"
        author_email = author_info.get("email") or commit_info.get("author_email") or "unknown@example.com"

        # Locate failed build info
        builds = payload.get("builds", [])
        failed_build = next((b for b in builds if str(b.get("id")) == ref.job_id or b.get("status") == "failed"), {})
        
        job_name = failed_build.get("name") or payload.get("build_name") or "build_job"
        stage = failed_build.get("stage") or payload.get("build_stage") or "test"
        failure_reason = failed_build.get("failure_reason") or payload.get("build_failure_reason") or "script_failure"
        ref_branch = attrs.get("ref") or payload.get("ref") or "main"
        web_url = attrs.get("url") or payload.get("repository", {}).get("homepage", "")

        # Changed files
        changed_files = []
        # Attempt to read log if present or via API
        raw_log = payload.get("log") or failed_build.get("trace") or ""
        api_url = creds.get("api_url", "https://gitlab.com/api/v4")
        token = creds.get("access_token")

        if not raw_log and token and ref.job_id.isdigit():
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(
                        f"{api_url}/projects/{payload.get('project_id')}/jobs/{ref.job_id}/trace",
                        headers={"PRIVATE-TOKEN": token}
                    )
                    if resp.status_code == 200:
                        raw_log = resp.text
            except Exception as e:
                logger.warning(f"Failed to fetch GitLab job trace via API: {e}")

        # Trim error portion and mask secrets
        sanitized_log = mask_secrets(trim_log(raw_log))

        return FailureEvent(
            event_key=ref.event_key,
            platform=self.key,
            project=project_name,
            branch=ref_branch,
            pipeline_id=ref.pipeline_id,
            url=web_url,
            job_id=ref.job_id,
            job_name=job_name,
            stage=stage,
            environment=attrs.get("environment"),
            failure_reason=failure_reason,
            log_excerpt=sanitized_log,
            commit_sha=commit_sha,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            changed_files=changed_files,
            change_request=str(payload.get("merge_request", {}).get("iid") or ""),
            urls={"pipeline": web_url, "job": f"{web_url}/-/jobs/{ref.job_id}" if web_url else ""},
            timestamps={"finished_at": None}
        )
