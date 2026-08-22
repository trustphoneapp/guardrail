from guardrail.graph import monitor_flagged, verifier_corroborated
from guardrail.models import MonitorResult, VerifierResult


def test_monitor_not_flagged_stops_pipeline():
    result = MonitorResult(flagged=False, deviation_score=0.0, reasons=[], signals=[], transaction_ids=[])
    assert monitor_flagged(result) is False


def test_monitor_flagged_continues():
    result = MonitorResult(flagged=True, deviation_score=0.8, reasons=["x"], signals=[], transaction_ids=["t1"])
    assert monitor_flagged(result) is True


def test_verifier_not_corroborated_stops_pipeline():
    result = VerifierResult(corroborated=False, confidence=0.1, corroborating_signals=[])
    assert verifier_corroborated(result) is False


def test_verifier_corroborated_continues():
    result = VerifierResult(
        corroborated=True, confidence=0.9, corroborating_signals=[], scam_pattern="gift_card_grandparent"
    )
    assert verifier_corroborated(result) is True
