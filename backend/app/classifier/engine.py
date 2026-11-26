import logging
from typing import Tuple
from app.models.event import FailureEvent
from app.classifier.rules import classify_by_rules
from app.classifier.llm_classifier import classify_with_claude

logger = logging.getLogger(__name__)

RULE_ACCEPT_THRESHOLD = 0.85
LLM_ACCEPT_THRESHOLD = 0.60

def classify_failure(event: FailureEvent, mode: str = "hybrid") -> Tuple[str, float, str, str]:
    """
    Combined classification engine implementing the architecture proposal:
    1. Rules first: if confidence >= 0.85 -> accept (fast, explainable).
    2. Claude LLM fallback: if rules are unsure.
    3. If LLM confidence < 0.60 or LLM is down -> 'needs review'.

    Supports evaluation modes: 'rules_only', 'llm_only', 'hybrid'.
    Returns: (category, confidence, evidence, source ['rules', 'llm', 'fallback'])
    """
    if mode == "rules_only":
        cat, conf, ev = classify_by_rules(event)
        return (cat, conf, ev, "rules")

    if mode == "llm_only":
        cat, conf, ev = classify_with_claude(event)
        source = "llm" if cat != "needs review" else "fallback"
        return (cat, conf, ev, source)

    # Hybrid mode (Default production flow)
    rule_cat, rule_conf, rule_ev = classify_by_rules(event)
    if rule_conf >= RULE_ACCEPT_THRESHOLD and rule_cat != "needs review":
        return (rule_cat, rule_conf, rule_ev, "rules")

    logger.info(f"Rule confidence {rule_conf:.2f} below threshold {RULE_ACCEPT_THRESHOLD}. Consulting Claude...")
    llm_cat, llm_conf, llm_ev = classify_with_claude(event)

    if llm_conf >= LLM_ACCEPT_THRESHOLD and llm_cat != "needs review":
        return (llm_cat, llm_conf, llm_ev, "llm")

    # If still unsure, or LLM was unavailable
    return ("needs review", 0.50, f"Low confidence ({rule_ev} | {llm_ev})", "fallback")
