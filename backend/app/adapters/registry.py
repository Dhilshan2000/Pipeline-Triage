from typing import Dict, Optional
from app.adapters.base import CIAdapter
from app.adapters.gitlab import GitLabAdapter
from app.adapters.github import GitHubAdapter

class AdapterRegistry:
    """Registry managing available CI input adapters."""
    def __init__(self):
        self._adapters: Dict[str, CIAdapter] = {
            "gitlab": GitLabAdapter(),
            "github": GitHubAdapter(),
        }

    def register(self, adapter: CIAdapter):
        self._adapters[adapter.key] = adapter

    def get(self, platform_key: str) -> Optional[CIAdapter]:
        return self._adapters.get(platform_key.lower())

    def detect_platform(self, headers: Dict[str, str]) -> Optional[str]:
        """Detects platform based on incoming webhook headers."""
        norm_headers = {k.lower(): v for k, v in headers.items()}
        if "x-gitlab-event" in norm_headers or "x-gitlab-token" in norm_headers:
            return "gitlab"
        if "x-github-event" in norm_headers or "x-hub-signature-256" in norm_headers:
            return "github"
        return None

adapter_registry = AdapterRegistry()
