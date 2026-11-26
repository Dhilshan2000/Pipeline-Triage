from typing import Protocol, Dict, Any, Optional
from app.models.event import FailureRef, RunStat, FailureEvent

class CIAdapter(Protocol):
    """
    Protocol that all CI input adapters must implement.
    The core never imports platform-specific code directly.
    """
    key: str # e.g. 'gitlab', 'github', 'bitbucket'
    config_schema: Dict[str, Any] # UI schema rendered on the Settings page

    def verify(self, headers: Dict[str, str], body: bytes, secret: Optional[str]) -> bool:
        """Verify webhook authenticity via secret token or HMAC signature."""
        ...

    def parse(self, headers: Dict[str, str], body: bytes) -> Optional[FailureRef | RunStat]:
        """
        Parse raw payload into a FailureRef (for failures to collect),
        RunStat (for counts), or None (ignore).
        """
        ...

    def collect(self, ref: FailureRef, creds: Dict[str, Any]) -> FailureEvent:
        """
        Execute read-only API calls to fetch full commit details, changed files,
        and logs, then return a standardized FailureEvent.
        """
        ...
