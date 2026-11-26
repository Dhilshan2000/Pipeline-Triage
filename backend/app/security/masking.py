import re
from typing import List

# Common secret regex patterns
SECRET_PATTERNS = [
    # GitLab Personal Access Token
    re.compile(r'glpat-[0-9a-zA-Z_\-]{20,}', re.IGNORECASE),
    # GitHub Personal Access Token (classic & fine-grained)
    re.compile(r'ghp_[0-9a-zA-Z]{36}', re.IGNORECASE),
    re.compile(r'github_pat_[0-9a-zA-Z_]{82}', re.IGNORECASE),
    # AWS Access Key ID & Secret Key
    re.compile(r'(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}', re.IGNORECASE),
    re.compile(r'(?i)aws_secret_access_key\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?'),
    # Private Key blocks
    re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----', re.MULTILINE),
    # URLs with embedded basic auth passwords
    re.compile(r'https?://[^:\s]+:([^@\s]+)@', re.IGNORECASE),
    # Common KEY=VALUE assignments with sensitive names
    re.compile(r'(?i)(?:password|token|secret|api_key|auth_key|access_key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.\$\!\@\#\%\^\&\*]{8,})["\']?'),
]

MASK_REPLACEMENT = "[MASKED_SECRET]"

def mask_secrets(text: str, known_secrets: List[str] | None = None) -> str:
    """
    Masks credentials, tokens, passwords, and known secrets before storing
    or passing text to an LLM.
    """
    if not text:
        return ""

    masked = text

    # First mask any explicitly known project secrets/tokens
    if known_secrets:
        for secret in known_secrets:
            if secret and len(secret) >= 4:
                masked = masked.replace(secret, MASK_REPLACEMENT)

    # Apply regex rules
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(MASK_REPLACEMENT, masked)

    return masked

def trim_log(log_text: str, max_lines: int = 250) -> str:
    """
    Isolate the error portion of the log:
    Keeps error traces and the final tail of the build log where failures occur.
    """
    if not log_text:
        return ""

    lines = log_text.splitlines()
    if len(lines) <= max_lines:
        return log_text

    # Locate error clues
    error_indices = [
        i for i, line in enumerate(lines)
        if re.search(r'(error|fail|exception|fatal|denied|unauthorized|timed? out)', line, re.IGNORECASE)
    ]

    if error_indices:
        # Window around the first detected serious error to the end
        start_idx = max(0, error_indices[0] - 20)
        selected_lines = lines[start_idx:start_idx + max_lines]
        return "\n".join(["[...log trimmed for brevity...]", *selected_lines])

    # Default to the tail of the log
    return "\n".join(["[...log trimmed for brevity...]", *lines[-max_lines:]])
