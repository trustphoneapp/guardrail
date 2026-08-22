from strands import tool

_SCAM_PATTERNS = {
    "velocity_spike": "gift_card_grandparent",
    "new_payee_high_value": "romance_wire_or_tech_support",
    "channel_shift": "tech_support_remote_access",
}

# Baseline MCC categories are friendly names ("groceries"), transactions carry
# numeric codes. This maps codes to the familiar categories so novelty means
# "outside her normal life", not "string mismatch".
_MCC_FAMILIES = {
    "5411": "groceries",
    "5912": "pharmacy",
    "4900": "utilities",
    "5812": "restaurants",
    "8011": "medical",
    "8062": "medical",
    "5732": "retail",
    "5999": "retail",
    "6300": "insurance",
}


@tool
def cross_check_signals(signals: list[dict], transactions: list[dict], baseline: dict) -> dict:
    """Independent corroboration: re-examines the raw transactions for features
    the Monitor's rules never look at, then requires BOTH a known scam-pattern
    match AND at least one independent feature. A Monitor flag with no
    independent evidence comes back not-corroborated, which is the honest path
    to the pipeline's quiet_unverified outcome.

    Independent features:
    - round_amounts: scam payments cluster on round figures (500, 300, 4200);
      real spending is 42.10 and 18.75.
    - tight_window: multiple transactions inside one hour.
    - unfamiliar_category: an MCC family absent from the elder's baseline
      spending distribution.
    """
    matched = [_SCAM_PATTERNS[s["kind"]] for s in signals if s["kind"] in _SCAM_PATTERNS]

    features: list[str] = []
    amounts = [float(t["amount"]) for t in transactions]
    if amounts and sum(1 for a in amounts if a >= 100 and a % 50 == 0) >= max(1, len(amounts) // 2):
        features.append("round_amounts")

    times = sorted(t["ts"] for t in transactions)
    if len(times) >= 2:
        # ts values arrive as ISO strings through the tool boundary
        from datetime import datetime

        parsed = [datetime.fromisoformat(str(x)) for x in times]
        gaps = [(b - a).total_seconds() for a, b in zip(parsed, parsed[1:])]
        if any(g <= 3600 for g in gaps):
            features.append("tight_window")

    known_families = set(baseline.get("mcc_distribution", {}))
    unfamiliar = [t for t in transactions if _MCC_FAMILIES.get(t.get("mcc", ""), "other") not in known_families]
    if unfamiliar:
        features.append("unfamiliar_category")

    corroborated = bool(matched) and bool(features)
    return {
        "corroborated": corroborated,
        "confidence": min(0.95, 0.55 + 0.15 * len(features)) if corroborated else 0.0,
        "corroborating_signals": signals if corroborated else [],
        "scam_pattern": matched[0] if matched else None,
        "independent_features": features,
    }
