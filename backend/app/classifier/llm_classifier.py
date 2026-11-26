import logging
from typing import Tuple, Dict, Any
from app.models.event import FailureEvent
from app.llm.provider import llm_provider
from app.classifier.rules import CATEGORIES

logger = logging.getLogger(__name__)

CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": CATEGORIES
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "evidence": {
            "type": "string"
        }
    },
    "required": ["category", "confidence", "evidence"],
    "additionalProperties": False
}

def classify_with_claude(event: FailureEvent) -> Tuple[str, float, str]:
    """
    Invokes Claude to classify ambiguous failures into one of the 8 categories.
    Enforces untrusted data boundaries and returns structured category + confidence.
    """
    system_prompt = (
        "You are an expert CI/CD failure classification engine.\n"
        "Your task is to classify a CI/CD build failure into exactly ONE of the 8 canonical categories:\n"
        f"{CATEGORIES}\n"
        "Output confidence between 0.0 and 1.0, along with a concise evidence string."
    )

    user_prompt = (
        f"CI Platform: {event.platform}\n"
        f"Project: {event.project}\n"
        f"Job Name: {event.job_name}\n"
        f"Pipeline Stage: {event.stage or 'N/A'}\n"
        f"Failure Reason: {event.failure_reason or 'N/A'}\n"
        "--- BEGIN SANITIZED BUILD LOG ---\n"
        f"{event.log_excerpt[:3000]}\n"
        "--- END SANITIZED BUILD LOG ---\n"
    )

    try:
        result = llm_provider.complete_structured(system_prompt, user_prompt, CLASSIFIER_SCHEMA)
        category = result.get("category", "needs review")
        confidence = float(result.get("confidence", 0.5))
        evidence = result.get("evidence", "Classified by Claude LLM")

        if category not in CATEGORIES:
            return ("needs review", 0.5, "Claude returned unknown category")

        return (category, confidence, f"Claude LLM: {evidence}")
    except Exception as e:
        logger.error(f"Claude classification failed or timed out: {e}")
        return ("needs review", 0.5, f"Claude unavailable ({str(e)[:50]}); fallback to review")
