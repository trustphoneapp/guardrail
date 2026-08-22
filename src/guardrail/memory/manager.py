from datetime import datetime

from guardrail.models import BaselineProfile, MonitorResult, TrendPoint
from guardrail.synthetic.baseline_generator import generate_baseline

# ponytail: in-process dict stands in for AgentCore Memory's actor-scoped long-term
# store. Swap for the real MemoryManager when deploying — the read/write shape
# (get_baseline/seed_baseline, keyed by actor_id) doesn't change.
_STORE: dict[str, BaselineProfile] = {}
_TREND: dict[str, list[TrendPoint]] = {}


def seed_baseline(actor_id: str) -> BaselineProfile:
    profile = generate_baseline(actor_id)
    _STORE[actor_id] = profile
    return profile


def get_baseline(actor_id: str) -> BaselineProfile:
    if actor_id not in _STORE:
        return seed_baseline(actor_id)
    return _STORE[actor_id]


def record_trend_point(actor_id: str, monitor_result: MonitorResult, scenario: str) -> TrendPoint:
    """Every Monitor run gets recorded, flagged or not — the trend view's whole
    point is showing the quiet days too, not just the alerts."""
    point = TrendPoint(
        ts=datetime.utcnow(),
        actor_id=actor_id,
        scenario=scenario,
        flagged=monitor_result.flagged,
        deviation_score=monitor_result.deviation_score,
    )
    _TREND.setdefault(actor_id, []).append(point)
    return point


def get_trend(actor_id: str, limit: int = 30) -> list[TrendPoint]:
    return _TREND.get(actor_id, [])[-limit:]
