from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class StatusHistoryEntry(BaseModel):
    from_status: Optional[str]
    to_status: str
    changed_by: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    comment: Optional[str] = None

class Comment(BaseModel):
    id: str
    user_email: str
    user_name: str
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Issue(BaseModel):
    """
    The unit people work on in the application.
    Repeated occurrences of the same failure update this issue rather than creating duplicates.
    """
    id: Optional[str] = Field(None, alias="_id")
    fingerprint: str = Field(..., description="project + job + category + normalised error")
    title: str
    status: str = Field("Open", description="Open | In progress | Resolved | Won't fix")
    is_open: bool = True
    assignee: Optional[str] = Field(None, description="Email of assigned user")
    category: str = Field(..., description="One of 8 failure categories")
    confidence: float = 1.0
    evidence: str = ""
    classifier_source: str = "rules" # "rules" | "llm" | "fallback"
    
    occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    latest_failure_id: Optional[str] = None
    event_key: str
    project: str
    branch: str
    pipeline_id: str
    job_name: str

    report: Optional[Dict[str, Any]] = None
    external_task_ids: Dict[str, str] = Field(default_factory=dict, description="e.g. {'kanvaro': 'TASK-123'}")
    
    comments: List[Comment] = Field(default_factory=list)
    status_history: List[StatusHistoryEntry] = Field(default_factory=list)

    class Config:
        populate_by_name = True
