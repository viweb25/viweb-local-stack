import pytest
from vi_core.results import Decision, safe_decision


@pytest.mark.parametrize(
    "result",
    [
        None,
        {},
        {"execution_status": "error", "decision": "PASS"},
        {"execution_status": "timeout", "decision": "PASS"},
        {"execution_status": "succeeded", "decision": "unknown"},
        {"execution_status": "succeeded"},
    ],
)
def test_untrusted_result_holds(result):
    assert safe_decision(result) == Decision.HOLD


@pytest.mark.parametrize("decision", list(Decision))
def test_successful_result_preserves_decision(decision):
    assert safe_decision({"execution_status": "succeeded", "decision": decision.value}) == decision
