from enum import Enum
from typing import Any


class Decision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"
    REINSPECT = "REINSPECT"


def safe_decision(result: dict[str, Any] | None) -> Decision:
    """Conservative simulation fallback, not a production rule engine.

    Invalid/missing/timeout results cannot grant PASS. Real rules must also check
    trigger sequence, freshness, configuration and model identity before PLC output.
    """
    if not result or result.get("execution_status") != "succeeded":
        return Decision.HOLD
    try:
        return Decision(result.get("decision"))
    except (ValueError, TypeError):
        return Decision.HOLD
