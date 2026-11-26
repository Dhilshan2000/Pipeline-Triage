from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RunStat(BaseModel):
    """Lightweight counter model for successful runs and merged PRs/MRs."""
    platform: str
    project: str
    kind: str # 'pipeline' or 'merge'
    status: str # 'success', 'merged'
    environment: Optional[str] = None
    finished_at: datetime = Field(default_factory=datetime.utcnow)

class FailureRef(BaseModel):
    """Reference parsed from initial webhook for lazy API collection."""
    platform: str
    event_key: str
    project: str
    pipeline_id: str
    job_id: str
    raw_payload: Dict[str, Any]

class FailureEvent(BaseModel):
    """
    Canonical FailureEvent model shared across all platforms (GitLab, GitHub, Bitbucket).
    Produced by CI adapters, consumed by triage core.
    """
    event_key: str = Field(..., description="Unique ID for dedupe: 'gitlab' or 'github' + project/repo + pipeline/run + job")
    platform: str = Field(..., description="'gitlab', 'github', etc.")
    project: str = Field(..., description="Repository full name / path_with_namespace")
    branch: str = Field(..., description="Branch name")
    pipeline_id: str = Field(..., description="Pipeline ID / Workflow Run ID")
    url: str = Field(..., description="Web URL to pipeline / workflow run")
    job_id: str = Field(..., description="Failed job / step ID")
    job_name: str = Field(..., description="Failed job name")
    stage: Optional[str] = Field(None, description="Pipeline stage or job step")
    environment: Optional[str] = Field(None, description="Deploy environment (Dev, QA, UAT, Prod) if known")
    failure_reason: Optional[str] = Field(None, description="Platform failure reason / conclusion")
    log_excerpt: str = Field("", description="Trimmed, masked error portion of the job log")
    commit_sha: str = Field(..., description="Head commit SHA that triggered the build")
    commit_message: str = Field(..., description="Head commit message (treated as untrusted data)")
    author_name: str = Field(..., description="Commit author name")
    author_email: str = Field(..., description="Commit author email (primary key for user routing)")
    changed_files: List[str] = Field(default_factory=list, description="List of files touched in commit")
    change_request: Optional[str] = Field(None, description="Associated MR/PR number or URL")
    urls: Dict[str, str] = Field(default_factory=dict, description="Related deep-links")
    timestamps: Dict[str, Optional[datetime]] = Field(default_factory=dict, description="started_at, finished_at")
