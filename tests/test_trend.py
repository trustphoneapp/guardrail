from guardrail.memory.manager import get_trend, record_trend_point
from guardrail.models import MonitorResult


def _monitor_result(flagged, score):
    return MonitorResult(flagged=flagged, deviation_score=score, reasons=[], signals=[], transaction_ids=[])


def test_quiet_and_flagged_both_recorded():
    record_trend_point("actor-trend-1", _monitor_result(False, 0.0), "quiet_day")
    record_trend_point("actor-trend-1", _monitor_result(True, 0.8), "grandparent_scam")
    points = get_trend("actor-trend-1")
    assert len(points) == 2
    assert points[0].flagged is False
    assert points[1].flagged is True
    assert points[1].deviation_score == 0.8


def test_trend_respects_limit():
    for i in range(5):
        record_trend_point("actor-trend-2", _monitor_result(False, 0.0), f"run-{i}")
    points = get_trend("actor-trend-2", limit=2)
    assert len(points) == 2
    assert points[-1].scenario == "run-4"


def test_empty_actor_returns_empty_list():
    assert get_trend("actor-never-seen") == []
