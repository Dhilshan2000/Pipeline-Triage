import re
from typing import Tuple, Optional
from app.models.event import FailureEvent

CATEGORIES = [
    "SonarQube quality gate",
    "Test failure",
    "Build / compile error",
    "Dependency problem",
    "Docker registry",
    "Deployment / server",
    "Runner / timeout",
    "Security scan"
]

def classify_by_rules(event: FailureEvent) -> Tuple[str, float, str]:
    """
    Deterministic rule-based classification over stage, job name, failure reason,
    and log excerpt.
    Returns: (category, confidence [0.0 - 1.0], evidence)
    """
    log_text = event.log_excerpt.lower()
    job_name = event.job_name.lower()
    stage = (event.stage or "").lower()
    reason = (event.failure_reason or "").lower()

    # 1. SonarQube quality gate
    if "sonarqube" in stage or "sonarqube" in job_name or "sonar" in job_name or "quality gate" in log_text:
        if "quality gate failed" in log_text or "coverage" in log_text or "status: error" in log_text:
            return ("SonarQube quality gate", 0.95, "Matched SonarQube stage/job and quality gate failure indicators in log")
        return ("SonarQube quality gate", 0.88, "Matched SonarQube job/stage name")

    # 2. Security scan
    if any(tool in job_name or tool in stage for tool in ["gitleaks", "trivy", "snyk", "bandit", "semgrep", "security"]):
        return ("Security scan", 0.95, f"Matched security scanner job name '{event.job_name}'")
    if "secret detected" in log_text or "vulnerability found" in log_text or "critical severity" in log_text:
        return ("Security scan", 0.90, "Security scan vulnerability / secret found in log text")

    # 3. Runner / timeout
    if reason in ["stuck_or_timeout_failure", "runner_system_failure", "timed_out"] or "timed out" in reason:
        return ("Runner / timeout", 0.95, f"Platform failure reason matches runner/timeout: {event.failure_reason}")
    if "no space left on device" not in log_text and ("runner offline" in log_text or "execution took longer than" in log_text or "job timed out" in log_text):
        return ("Runner / timeout", 0.90, "Matched runner offline or job timeout patterns in log")

    # 4. Docker registry
    if any(k in job_name or k in stage for k in ["push", "docker", "registry"]):
        if any(err in log_text for err in ["denied", "unauthorized", "authentication required", "no basic auth credentials"]):
            return ("Docker registry", 0.95, "Matched registry authorization/permission error during image push")
    if "denied: access forbidden" in log_text or "unauthorized: authentication required" in log_text:
        return ("Docker registry", 0.90, "Registry authentication error in log")

    # 5. Dependency problem
    if any(err in log_text for err in [
        "npm err! eresolve", "no matching version", "could not resolve dependencies",
        "pip: no matching distribution", "module not found", "cannot find module",
        "package not found", "poetry: solverproblem"
    ]):
        return ("Dependency problem", 0.92, "Matched dependency conflict or missing package pattern in log")

    # 6. Deployment / server
    if "deploy" in stage or "deploy" in job_name:
        if any(err in log_text for err in ["no space left on device", "connection timed out", "connection refused", "502 bad gateway", "host unreachable"]):
            return ("Deployment / server", 0.95, "Deployment stage failed with server/connection/disk issue")
    if "no space left on device" in log_text or "connection refused" in log_text or "could not resolve host" in log_text:
        return ("Deployment / server", 0.88, "Matched server resource or connectivity error in log")

    # 7. Test failure
    if any(k in stage or k in job_name for k in ["test", "unit", "e2e", "jest", "pytest"]):
        if any(err in log_text for err in ["fail", "failed", "assertionerror", "failures:", "tests failed", "expect("]):
            return ("Test failure", 0.92, "Matched test suite failure in test job")
    if "assertionerror" in log_text or "expected:" in log_text or "failed tests:" in log_text:
        return ("Test failure", 0.86, "Assertion error or failed test pattern present in log")

    # 8. Build / compile error
    if any(k in stage or k in job_name for k in ["build", "compile"]):
        if any(err in log_text for err in ["syntaxerror", "compilation error", "error ts", "javac", "build failed"]):
            return ("Build / compile error", 0.92, "Matched syntax or compilation error in build stage")
    if "syntaxerror" in log_text or "tsc error" in log_text or "compile error" in log_text:
        return ("Build / compile error", 0.86, "Compile or syntax error signature in log")

    # Low confidence fallback
    return ("needs review", 0.40, "No definitive rule match found; requires LLM evaluation")
