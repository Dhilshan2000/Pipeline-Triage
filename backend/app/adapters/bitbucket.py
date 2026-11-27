import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
import httpx

from app.models.event import FailureRef, RunStat, FailureEvent
from app.security.masking import trim_log, mask_secrets

logger = logging.getLogger(__name__)


class BitbucketAdapter:
    """Bitbucket Pipelines input adapter implementing CIAdapter."""

    key: str = "bitbucket"
    config_schema: Dict[str, Any] = {
        "title": "Bitbucket Pipelines Configuration",
        "properties": {
            "api_url": {
                "type": "string",
                "default": "https://api.bitbucket.org/2.0",
                "description": "Bitbucket API Base URL",
            },
            "webhook_secret": {
                "type": "string",
                "secret": True,
                "description": "Secret configured in Bitbucket webhook (HMAC-SHA256)",
            },
            "access_token": {
                "type": "string",
                "secret": True,
                "description": "Repository access token (Repositories & Pipelines: Read)",
            },
        },
        "required": ["webhook_secret"],
    }

    def verify(self, headers: Dict[str, str], body: bytes, secret: Optional[str]) -> bool:
        """Verify Bitbucket webhook HMAC-SHA256 signature (X-Hub-Signature)."""
        if not secret:
            return True
        sig = headers.get("x-hub-signature") or headers.get("X-Hub-Signature")
        if not sig or not sig.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)

    def parse(self, headers: Dict[str, str], body: bytes) -> Optional[FailureRef | RunStat]:
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse Bitbucket webhook JSON: {e}")
            return None

        repo_name = data.get("repository", {}).get("full_name", "unknown/repo")
        pipeline = data.get("pipeline") or data.get("commit_status") or {}
        state = pipeline.get("state", {})
        result_name = (state.get("result", {}).get("name") or pipeline.get("state") or "").upper()
        pipeline_id = str(pipeline.get("uuid") or pipeline.get("build_number") or "0")

        if result_name in ("SUCCESSFUL", "SUCCESS"):
            return RunStat(
                platform=self.key,
                project=repo_name,
                kind="pipeline",
                status="success",
            )
        if result_name in ("FAILED", "ERROR", "STOPPED"):
            step = data.get("step", {})
            job_id = str(step.get("uuid") or "pipeline_failed")
            event_key = f"bitbucket:{repo_name}:{pipeline_id}:{job_id}"
            return FailureRef(
                platform=self.key,
                event_key=event_key,
                project=repo_name,
                pipeline_id=pipeline_id,
                job_id=job_id,
                raw_payload=data,
            )

        return None

    def collect(self, ref: FailureRef, creds: Dict[str, Any]) -> FailureEvent:
        payload = ref.raw_payload
        pipeline = payload.get("pipeline") or {}
        step = payload.get("step") or {}
        target = pipeline.get("target") or {}
        commit = target.get("commit") or payload.get("commit") or {}

        commit_sha = commit.get("hash") or "unknown_sha"
        commit_message = commit.get("message") or "No commit message"
        author_raw = (commit.get("author") or {}).get("raw") or ""
        author_name = author_raw.split("<")[0].strip() or "Unknown Author"
        author_email = (
            author_raw.split("<")[1].rstrip(">").strip()
            if "<" in author_raw and ">" in author_raw
            else "unknown@example.com"
        )

        job_name = step.get("name") or pipeline.get("name") or "bitbucket-pipeline"
        stage = step.get("stage") or "build"
        ref_branch = target.get("ref_name") or "main"
        html_url = (pipeline.get("links") or {}).get("html", {}).get("href", "")

        raw_log = payload.get("log") or ""
        token = creds.get("access_token")
        api_url = creds.get("api_url", "https://api.bitbucket.org/2.0")
        if not raw_log and token and ref.job_id != "pipeline_failed":
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(
                        f"{api_url}/repositories/{ref.project}/pipelines/{ref.pipeline_id}/steps/{ref.job_id}/log",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code == 200:
                        raw_log = resp.text
            except Exception as e:
                logger.warning(f"Failed to fetch Bitbucket step log via API: {e}")

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
            failure_reason="failed",
            log_excerpt=sanitized_log,
            commit_sha=commit_sha,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            changed_files=[],
            change_request="",
            urls={"pipeline": html_url},
            timestamps={"finished_at": None},
        )
