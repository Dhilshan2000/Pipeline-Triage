import logging
from typing import Dict, Any, List, Optional
from app.models.event import FailureEvent
from app.models.report import TriageReport, FileLocation, FixStep
from app.rag.knowledge_base import knowledge_base
from app.llm.provider import llm_provider

logger = logging.getLogger(__name__)

REPORT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One sentence: what failed."},
        "root_cause": {"type": "string", "description": "Why it happened, grounded in the log and knowledge base."},
        "category": {"type": "string"},
        "files_and_lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_number": {"type": ["integer", "null"]},
                    "author": {"type": ["string", "null"]}
                },
                "required": ["file_path"]
            }
        },
        "fix_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_number": {"type": "integer"},
                    "instruction": {"type": "string"},
                    "code_or_command": {"type": ["string", "null"]}
                },
                "required": ["step_number", "instruction"]
            }
        },
        "permanent_fix": {"type": ["string", "null"]},
        "effort_estimate": {"type": "string"},
        "similar_failures": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["summary", "root_cause", "category", "fix_steps", "effort_estimate"],
    "additionalProperties": False
}

def generate_rule_fallback_report(event: FailureEvent, category: str, sonar_data: Optional[Dict[str, Any]] = None) -> TriageReport:
    """Fast deterministic rule-based report when LLM is slow (>45s) or down."""
    summary = f"Job '{event.job_name}' failed in stage '{event.stage or 'build'}' ({category})."
    root_cause = f"The pipeline encountered a {category} failure. Error signal: {event.failure_reason or 'Command returned non-zero exit status'}."
    files: List[FileLocation] = []

    if sonar_data and sonar_data.get("issues"):
        for iss in sonar_data["issues"][:3]:
            files.append(
                FileLocation(
                    file_path=iss.get("component", "unknown"),
                    line_number=iss.get("line"),
                    author=iss.get("author")
                )
            )

    fix_steps = [
        FixStep(
            step_number=1,
            instruction=f"Check the failure log output around stage '{event.stage or event.job_name}'.",
            code_or_command=None
        ),
        FixStep(
            step_number=2,
            instruction="Apply the corrective fix and verify locally before pushing changes.",
            code_or_command=f"git checkout {event.branch} && git pull"
        )
    ]

    return TriageReport(
        summary=summary,
        root_cause=root_cause,
        category=category,
        files_and_lines=files,
        fix_steps=fix_steps,
        permanent_fix="Verify pipeline dependencies and tests in local pre-commit checks.",
        effort_estimate="15-30 minutes",
        similar_failures=[],
        sources=["Rule-based fallback summary"]
    )

def generate_triage_report(
    event: FailureEvent,
    category: str,
    sonar_data: Optional[Dict[str, Any]] = None
) -> TriageReport:
    """
    RAG + Claude LLM report generator:
    1. Retrieves relevant runbooks and documentation from Qdrant.
    2. Builds grounded prompt including exact SonarQube facts.
    3. Calls Claude with strict 45s timeout constraint and JSON schema.
    4. Falls back to deterministic rule summary if unavailable.
    """
    # 1. RAG retrieval
    search_query = f"{category} {event.job_name} {event.log_excerpt[:200]}"
    rag_chunks = knowledge_base.search(search_query, category=category, limit=3)
    sources = [c.get("reference") or c.get("title", "runbook") for c in rag_chunks]

    # Context formatting
    context_str = "\n\n".join([
        f"--- Source: {c.get('title')} ({c.get('reference')}) ---\n{c.get('text')}"
        for c in rag_chunks
    ])

    system_prompt = (
        "You are an expert CI/CD triage engineer generating a structured diagnosis report.\n"
        "Your report must be grounded in the provided runbooks and build logs.\n"
        "Provide clear, numbered steps with actual code or commands to resolve the issue immediately."
    )

    user_prompt = (
        f"Project: {event.project}\n"
        f"Branch: {event.branch}\n"
        f"Pipeline ID: {event.pipeline_id}\n"
        f"Failed Job: {event.job_name} (Stage: {event.stage or 'N/A'})\n"
        f"Category: {category}\n"
        f"Commit: {event.commit_sha[:8]} by {event.author_name} ({event.author_email})\n"
        f"Commit Message: {event.commit_message}\n\n"
        "KNOWLEDGE BASE RUNBOOKS:\n"
        f"{context_str}\n\n"
        "SONARQUBE ANALYSIS FACTS:\n"
        f"{sonar_data or 'None'}\n\n"
        "TRIMMED & SANITIZED BUILD LOG:\n"
        f"{event.log_excerpt[:3500]}\n"
    )

    try:
        data = llm_provider.complete_structured(system_prompt, user_prompt, REPORT_JSON_SCHEMA)
        # Ensure sources list includes RAG retrieved docs
        if not data.get("sources"):
            data["sources"] = sources
        return TriageReport(**data)
    except Exception as e:
        logger.warning(f"Claude report generation failed or timed out ({e}); generating rule fallback report.")
        fallback = generate_rule_fallback_report(event, category, sonar_data)
        if sources:
            fallback.sources.extend(sources)
        return fallback
