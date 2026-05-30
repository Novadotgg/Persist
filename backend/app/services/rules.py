import re
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger()

# Deterministic triage rules
PRIORITY_SENDERS = [
    "boss@company.com",
    "manager@company.com",
    "alerts@system.com"
]

URGENT_KEYWORDS = [
    r"\bprod\b",
    r"\boutage\b",
    r"\bcritical\b",
    r"\bemergency\b",
    r"\bdown\b",
    r"\bbroken\b"
]

def match_triage_rules(payload: Dict[str, Any]) -> Optional[int]:
    """
    Screens incoming events for deterministic priority overrides.
    Returns:
        - int (1-5) representing priority if a rule matches.
        - None if no rules match (falling back to AI classifier).
    """
    sender = payload.get("sender", "").lower()
    subject = payload.get("subject", "").lower()
    body = payload.get("body", "").lower()

    # Rule 1: Check priority senders
    if sender in PRIORITY_SENDERS:
        logger.info("Rule matched: Priority Sender identified", sender=sender)
        return 5  # Critical

    # Rule 2: Check urgent keywords in subject/body
    for pattern in URGENT_KEYWORDS:
        if re.search(pattern, subject) or re.search(pattern, body):
            logger.info("Rule matched: Urgent keyword detected", pattern=pattern)
            return 4  # High

    # Rule 3: Check explicitly defined low-priority senders
    if "newsletter@" in sender or "no-reply@" in sender:
        logger.info("Rule matched: Newsletter / Bot Sender", sender=sender)
        return 1  # Low

    return None
