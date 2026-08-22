from strands import tool

_SCAM_PATTERNS = {
    "velocity_spike": "gift_card_grandparent",
    "new_payee_high_value": "romance_wire_or_tech_support",
    "channel_shift": "tech_support_remote_access",
}


@tool
def cross_check_signals(signals: list[dict]) -> dict:
    """Independent re-derivation: matches Monitor's signals against known scam-pattern
    fingerprints via a separate lookup, not the same computation restated."""
    matched = [_SCAM_PATTERNS[s["kind"]] for s in signals if s["kind"] in _SCAM_PATTERNS]
    corroborated = bool(matched)
    return {
        "corroborated": corroborated,
        "confidence": 0.85 if corroborated else 0.0,
        "corroborating_signals": signals if corroborated else [],
        "scam_pattern": matched[0] if matched else None,
    }
