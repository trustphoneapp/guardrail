import re

from strands import tool

from guardrail.memory.manager import get_baseline

# Matches "GiftCard", "Gift Card", "Gift-Card", "Vanilla Visa Prepaid",
# "Green Dot MoneyPak", "Reload". The original check was the literal substring
# "giftcard" after stripping spaces, which "Target Gift-Card" walked straight
# past. MCC 6051 is quasi-cash (prepaid/stored value), the code a card network
# assigns to these even when the merchant name says nothing.
_GIFT_CARD_RE = re.compile(r"gift\s*-?\s*card|prepaid|moneypak|reload|vanilla", re.IGNORECASE)
_QUASI_CASH_MCC = "6051"

# Absolute floors so a small baseline does not make a small legitimate payment
# look like fraud. seed-42 median is $18.13, so "10x median" alone flagged a
# $200 hospital wire as a romance scam. Both conditions must hold.
SINGLE_GIFT_CARD_FLOOR = 500.0
WIRE_ABSOLUTE_FLOOR = 1000.0
WIRE_MEDIAN_MULTIPLIER = 10


def _is_gift_card(t: dict) -> bool:
    return bool(_GIFT_CARD_RE.search(t["merchant_name"])) or t.get("mcc") == _QUASI_CASH_MCC


@tool
def get_behavioral_baseline(actor_id: str) -> dict:
    """Read the elder's behavioral baseline. In the demo build this is an
    in-process store (memory/manager.py) shaped like AgentCore Memory's
    actor-scoped long-term store; the swap is the store, not this tool."""
    return get_baseline(actor_id).model_dump(mode="json")


@tool
def score_deviation(transactions: list[dict], baseline: dict) -> dict:
    """Deterministic scoring — no LLM math. Flags gift-card bursts and outsized
    wires against the baseline's cadence."""
    reasons: list[str] = []
    signals: list[dict] = []

    # "This was Mom": merchants the family dismissed are her normal now.
    allowlist = {m.lower() for m in baseline.get("allowlist", [])}
    if allowlist:
        transactions = [t for t in transactions if t["merchant_name"].lower() not in allowlist]

    gift_card_hits = [t for t in transactions if _is_gift_card(t)]
    big_single_gift_card = [t for t in gift_card_hits if float(t["amount"]) >= SINGLE_GIFT_CARD_FLOOR]
    if len(gift_card_hits) >= 2:
        reasons.append(f"{len(gift_card_hits)} gift-card purchases in one window")
        signals.append({"kind": "velocity_spike", "severity": 0.8, "evidence": {"count": len(gift_card_hits)}})
    elif big_single_gift_card:
        # One $2,000 gift card is not a burst, but it is not a birthday either.
        reasons.append("single large gift-card purchase")
        signals.append({"kind": "velocity_spike", "severity": 0.7, "evidence": {"count": 1}})

    median_amount = baseline["cadence_hist"]["median_amount"]
    big_wires = [
        t
        for t in transactions
        if t["channel"] == "wire"
        and float(t["amount"]) > median_amount * WIRE_MEDIAN_MULTIPLIER
        and float(t["amount"]) >= WIRE_ABSOLUTE_FLOOR
    ]
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
