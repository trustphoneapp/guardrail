from strands import tool

from guardrail.memory.manager import get_baseline


@tool
def get_behavioral_baseline(actor_id: str) -> dict:
    """Read the elder's durable behavioral baseline from AgentCore Memory."""
    return get_baseline(actor_id).model_dump(mode="json")


@tool
def score_deviation(transactions: list[dict], baseline: dict) -> dict:
    """Deterministic scoring — no LLM math. Flags gift-card bursts and outsized
    wires against the baseline's cadence."""
    reasons: list[str] = []
    signals: list[dict] = []

    gift_card_hits = [t for t in transactions if "giftcard" in t["merchant_name"].lower().replace(" ", "")]
    if len(gift_card_hits) >= 2:
        reasons.append(f"{len(gift_card_hits)} gift-card purchases in one window")
        signals.append({"kind": "velocity_spike", "severity": 0.8, "evidence": {"count": len(gift_card_hits)}})

    median_amount = baseline["cadence_hist"]["median_amount"]
    big_wires = [t for t in transactions if t["channel"] == "wire" and float(t["amount"]) > median_amount * 10]
    if big_wires:
        reasons.append("wire transfer far above baseline median")
        signals.append({"kind": "new_payee_high_value", "severity": 0.9, "evidence": {"count": len(big_wires)}})

    # tech-support scam pattern: a remote-access/software purchase (mcc 7379)
    # followed by a cash withdrawal in the same window — the purchase is the
    # "install this to fix your computer" step, the ATM run is the scammer
    # cashing out. Neither the gift-card nor the wire rule above catches this.
    remote_access_hits = [t for t in transactions if t["mcc"] == "7379"]
    atm_hits = [t for t in transactions if t["channel"] == "atm"]
    if remote_access_hits and atm_hits:
        reasons.append("remote-access software purchase followed by ATM withdrawal")
        signals.append({"kind": "channel_shift", "severity": 0.85, "evidence": {"atm_count": len(atm_hits)}})

    return {
        "flagged": bool(reasons),
        "deviation_score": max((s["severity"] for s in signals), default=0.0),
        "reasons": reasons,
        "signals": signals,
        "transaction_ids": [t["txn_id"] for t in transactions],
    }
