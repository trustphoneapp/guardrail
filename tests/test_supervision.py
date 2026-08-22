"""The steering guard, the Verifier's independence, and the dismiss loop."""

from guardrail.memory.manager import add_to_allowlist, get_baseline, seed_baseline
from guardrail.steering import EscalationGuard
from guardrail.tools.baseline_tools import score_deviation
from guardrail.tools.corroboration_tools import cross_check_signals

# --- EscalationGuard: the model cannot route an approval elsewhere ---


def _tool_use(name, **inp):
    return {"toolUseId": "t1", "name": name, "input": inp}


def test_guard_blocks_wrong_actor():
    g = EscalationGuard("alert-1", "sarla-demo-001")
    action = g.steer_before_tool(
        agent=None, tool_use=_tool_use("request_human_approval", alert_id="alert-1", actor_id="someone-else")
    )
    assert type(action).__name__ == "Guide"
    assert "sarla-demo-001" in action.reason


def test_guard_blocks_wrong_alert():
    g = EscalationGuard("alert-1", "sarla-demo-001")
    action = g.steer_before_tool(
        agent=None, tool_use=_tool_use("request_human_approval", alert_id="alert-OTHER", actor_id="sarla-demo-001")
    )
    assert type(action).__name__ == "Guide"


def test_guard_allows_correct_args_and_other_tools():
    g = EscalationGuard("alert-1", "sarla-demo-001")
    ok = g.steer_before_tool(
        agent=None, tool_use=_tool_use("request_human_approval", alert_id="alert-1", actor_id="sarla-demo-001")
    )
    assert type(ok).__name__ == "Proceed"
    other = g.steer_before_tool(agent=None, tool_use=_tool_use("draft_alert", verdict={}, evidence=[], actor_id="x"))
    assert type(other).__name__ == "Proceed"


# --- Verifier independence: pattern match alone is not corroboration ---

SIGNALS = [{"kind": "velocity_spike", "severity": 0.8, "evidence": {"count": 3}}]
BASELINE = {"mcc_distribution": {"groceries": 0.5, "pharmacy": 0.5}}


def _txn(merchant, mcc, amount, ts):
    return {"merchant_name": merchant, "mcc": mcc, "amount": amount, "ts": ts, "channel": "card_not_present"}


def test_corroborated_needs_pattern_AND_independent_feature():
    # round amounts in a tight window: two independent features
    txns = [
        _txn("Target GiftCard", "5732", "500", "2026-08-22T10:00:00"),
        _txn("CVS GiftCard", "5912", "500", "2026-08-22T10:30:00"),
    ]
    out = cross_check_signals(signals=SIGNALS, transactions=txns, baseline=BASELINE)
    assert out["corroborated"] is True
    assert "round_amounts" in out["independent_features"]
    assert "tight_window" in out["independent_features"]


def test_pattern_without_features_is_not_corroborated():
    # a matching signal kind, but ordinary amounts, spread out, familiar categories
    txns = [
        _txn("Safeway", "5411", "42.10", "2026-08-20T10:00:00"),
        _txn("CVS Pharmacy", "5912", "18.75", "2026-08-21T15:00:00"),
    ]
    out = cross_check_signals(signals=SIGNALS, transactions=txns, baseline=BASELINE)
    assert out["corroborated"] is False


def test_features_without_pattern_is_not_corroborated():
    txns = [_txn("Western Union", "4829", "4200", "2026-08-22T10:00:00")]
    out = cross_check_signals(signals=[{"kind": "unknown_kind", "severity": 1, "evidence": {}}], transactions=txns, baseline=BASELINE)
    assert out["corroborated"] is False


# --- Close the loop: a dismissal changes the next run ---


def test_dismissed_merchants_quiet_the_next_run():
    seed_baseline("loop-actor")
    txns = [
        {"txn_id": "t1", "merchant_name": "Target GiftCard", "mcc": "5411", "channel": "card_not_present", "amount": "500"},
        {"txn_id": "t2", "merchant_name": "CVS GiftCard", "mcc": "5912", "channel": "card_not_present", "amount": "500"},
    ]
    baseline = get_baseline("loop-actor").model_dump(mode="json")
    assert score_deviation(transactions=txns, baseline=baseline)["flagged"] is True

    add_to_allowlist("loop-actor", ["Target GiftCard", "CVS GiftCard"])
    baseline_after = get_baseline("loop-actor").model_dump(mode="json")
    assert score_deviation(transactions=txns, baseline=baseline_after)["flagged"] is False


def test_allowlist_does_not_blind_other_merchants():
    seed_baseline("loop-actor-2")
    add_to_allowlist("loop-actor-2", ["Target GiftCard"])
    txns = [
        {"txn_id": "t1", "merchant_name": "Apple GiftCard", "mcc": "5732", "channel": "card_not_present", "amount": "500"},
        {"txn_id": "t2", "merchant_name": "Best Buy GiftCard", "mcc": "5732", "channel": "card_not_present", "amount": "500"},
    ]
    baseline = get_baseline("loop-actor-2").model_dump(mode="json")
    assert score_deviation(transactions=txns, baseline=baseline)["flagged"] is True
