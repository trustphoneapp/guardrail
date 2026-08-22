from datetime import datetime

from guardrail import store
from guardrail.models import Alert, BaselineProfile, MonitorResult, TrendPoint
from guardrail.synthetic.baseline_generator import generate_baseline

# All state goes through guardrail.store: a dict in tests, DynamoDB when
# GUARDRAIL_TABLE is set, so the runtime container and the dashboard see the
# same baselines, trend rows, and alerts. The shape mirrors AgentCore Memory's
# actor-scoped long-term store; the swap to it would be inside store.py.

_BASELINE = "BASELINE"
_TREND = "TREND"
_ALERT = "ALERTBODY"


def seed_baseline(actor_id: str) -> BaselineProfile:
    profile = generate_baseline(actor_id)
    store.put(_BASELINE, actor_id, profile.model_dump(mode="json"))
    return profile


def get_baseline(actor_id: str) -> BaselineProfile:
    raw = store.get(_BASELINE, actor_id)
    if raw is None:
        return seed_baseline(actor_id)
    return BaselineProfile(**raw)


def add_to_allowlist(actor_id: str, merchants: list[str]) -> BaselineProfile:
    """The family's dismiss decision, applied to the elder's baseline so the
    next run treats these merchants as her normal."""
    profile = get_baseline(actor_id)
    known = {m.lower() for m in profile.allowlist}
    profile.allowlist.extend(m for m in merchants if m.lower() not in known)
    store.put(_BASELINE, actor_id, profile.model_dump(mode="json"))
    return profile


def record_trend_point(
    actor_id: str, monitor_result: MonitorResult, scenario: str, audit: list[dict] | None = None
) -> TrendPoint:
    """Every Monitor run gets recorded, flagged or not. The trend view's whole
    point is showing the quiet days too, not just the alerts."""
    point = TrendPoint(
        ts=datetime.utcnow(),
        actor_id=actor_id,
        scenario=scenario,
        flagged=monitor_result.flagged,
        deviation_score=monitor_result.deviation_score,
        audit=audit or [],
    )
    store.append(f"{_TREND}#{actor_id}", point.model_dump(mode="json"))
    return point


def get_trend(actor_id: str, limit: int = 30) -> list[TrendPoint]:
    return [TrendPoint(**row) for row in store.list_(f"{_TREND}#{actor_id}", limit=limit)]


def save_alert(alert: Alert) -> None:
    """Persisted so the dashboard can render the real evidence trail after the
    PIN, from a different process than the one that produced it."""
    store.put(_ALERT, alert.alert_id, alert.model_dump(mode="json"))


def get_alert(alert_id: str) -> Alert | None:
    raw = store.get(_ALERT, alert_id)
    return Alert(**raw) if raw else None
