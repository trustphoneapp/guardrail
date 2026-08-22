"""Exercises run_pipeline end to end with stubbed agents and zero Bedrock calls.

Nothing else in the suite drove run_pipeline before this file existed, which is
how the fail-open bug shipped: each stage was tested alone and the routing
between them was not. These tests are the routing."""

from types import SimpleNamespace

import pytest

from guardrail.graph import FAIL_OPEN_REASON, run_pipeline
from guardrail.models import MonitorResult, Signal, VerifierResult


class FakeAgent:
    """Returns a fixed structured_output; records the prompts it was given."""

    def __init__(self, structured_output=None):
        self.structured_output = structured_output
        self.calls = []

    def __call__(self, prompt, **kwargs):
        self.calls.append(prompt)
        return SimpleNamespace(structured_output=self.structured_output)


class Boom:
    """An agent whose every invocation raises, as if Bedrock were down."""

    calls = 0

    def __call__(self, *a, **k):
        Boom.calls += 1
        raise RuntimeError("bedrock down")


FLAGGED = MonitorResult(
    flagged=True,
    deviation_score=0.8,
    reasons=["3 gift-card purchases in one window"],
    signals=[Signal(kind="velocity_spike", severity=0.8, evidence={"count": 3})],
    transaction_ids=["t1", "t2", "t3"],
)
QUIET = MonitorResult(flagged=False, deviation_score=0.0, reasons=[], signals=[], transaction_ids=["t1"])
CORROBORATED = VerifierResult(
    corroborated=True, confidence=0.85, corroborating_signals=FLAGGED.signals, scam_pattern="gift_card_grandparent"
)
NOT_CORROBORATED = VerifierResult(corroborated=False, confidence=0.0, corroborating_signals=[], scam_pattern=None)


@pytest.fixture(autouse=True)
def silence_notify(monkeypatch):
    monkeypatch.setattr("guardrail.approval.channel.notify", lambda **k: None)


def test_quiet_day_stops_after_monitor():
    verifier = FakeAgent(CORROBORATED)
    out = run_pipeline(FakeAgent(QUIET), verifier, FakeAgent(), "acct-1", "sarla-demo-001", "quiet_day", "alert-q")
    assert out["status"] == "quiet"
    assert verifier.calls == []
    assert "alert" not in out


def test_flag_plus_corroboration_escalates_with_real_token():
    out = run_pipeline(
        FakeAgent(FLAGGED), FakeAgent(CORROBORATED), FakeAgent(), "acct-1", "sarla-demo-001", "grandparent_scam", "alert-e"
    )
    assert out["status"] == "escalated"
    token = out["alert"]["approval_token"]
    assert token["actor_id"] == "sarla-demo-001"
    assert token["alert_id"] == "alert-e"
    assert token["scope"] == "alert:approve_deny"


def test_verifier_rejection_stays_quiet():
    out = run_pipeline(
        FakeAgent(FLAGGED), FakeAgent(NOT_CORROBORATED), FakeAgent(), "acct-1", "sarla-demo-001", "grandparent_scam", "alert-u"
    )
    assert out["status"] == "quiet_unverified"
    assert "alert" not in out


def test_monitor_outage_fails_open_to_a_human():
    # Reproduced the original bug: Monitor's fallback has signals=[], the
    # Verifier's deterministic lookup on [] says not corroborated, and a Bedrock
    # outage produced silence. This asserts the fix: escalation, no model call.
    Boom.calls = 0
    verifier = FakeAgent(NOT_CORROBORATED)  # would say "no" if asked; it must not be asked
    out = run_pipeline(Boom(), verifier, Boom(), "acct-1", "sarla-demo-001", "grandparent_scam", "alert-fo")
    assert out["status"] == "escalated"
    assert out["monitor"]["reasons"] == [FAIL_OPEN_REASON]
    assert out["verifier"]["scam_pattern"] == FAIL_OPEN_REASON
    assert verifier.calls == [], "Verifier must be bypassed when Monitor failed; nothing to corroborate"
    assert out["alert"]["approval_token"]["actor_id"] == "sarla-demo-001"


def test_verifier_outage_also_fails_open():
    Boom.calls = 0
    out = run_pipeline(FakeAgent(FLAGGED), Boom(), Boom(), "acct-1", "sarla-demo-001", "grandparent_scam", "alert-vo")
    assert out["status"] == "escalated"
    assert out["verifier"]["scam_pattern"] == FAIL_OPEN_REASON
