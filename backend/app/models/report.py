from typing import List, Optional
from pydantic import BaseModel, Field

class FileLocation(BaseModel):
    file_path: str = Field(..., description="Relative file path where the error occurred")
    line_number: Optional[int] = Field(None, description="Line number if identifiable")
    author: Optional[str] = Field(None, description="Who wrote or touched this file/line")

class FixStep(BaseModel):
    step_number: int
    instruction: str
    code_or_command: Optional[str] = None

class TriageReport(BaseModel):
    """
    Validated JSON report structure produced by LLM or rule-based fallback.
    """
    summary: str = Field(..., description="One sentence: what failed.")
    root_cause: str = Field(..., description="Why it happened, grounded in log and knowledge base.")
    category: str = Field(..., description="One of the 8 canonical categories")
    files_and_lines: List[FileLocation] = Field(default_factory=list, description="Exact files and lines from CI and SonarQube")
    fix_steps: List[FixStep] = Field(default_factory=list, description="Numbered actionable steps with commands or code to fix now")
    permanent_fix: Optional[str] = Field(None, description="How to prevent this from repeating if a pattern exists")
    effort_estimate: str = Field("15-30 minutes", description="Estimated time to resolve")
    similar_failures: List[str] = Field(default_factory=list, description="References to similar past failure fingerprints or issue IDs")
    sources: List[str] = Field(default_factory=list, description="Runbooks, Sonar rules, and docs used to ground the fix")
