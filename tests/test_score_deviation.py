from guardrail.tools.baseline_tools import score_deviation

BASELINE = {"cadence_hist": {"median_amount": 20.0}}


def _txn(txn_id, merchant, mcc, channel, amount):
    return {"txn_id": txn_id, "merchant_name": merchant, "mcc": mcc, "channel": channel, "amount": amount}


def test_quiet_day_not_flagged():
    txns = [_txn("t1", "Safeway", "5411", "card_not_present", "42.10")]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is False
    assert result["reasons"] == []


def test_gift_card_burst_flagged():
    txns = [
        _txn("t1", "Target GiftCard", "5411", "card_not_present", "500"),
        _txn("t2", "CVS GiftCard", "5912", "card_not_present", "500"),
    ]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is True
    assert "gift-card" in result["reasons"][0]
    assert result["signals"][0]["kind"] == "velocity_spike"


def test_big_wire_flagged():
    txns = [_txn("t1", "Western Union", "4829", "wire", "4200")]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is True
    assert "wire" in result["reasons"][0]
    assert result["signals"][0]["kind"] == "new_payee_high_value"


def test_tech_support_pattern_flagged():
    txns = [
        _txn("t1", "GeekSquad Remote", "7379", "card_not_present", "299"),
        _txn("t2", "ATM Withdrawal", "6011", "atm", "800"),
    ]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is True
    assert "ATM" in result["reasons"][0]
    assert result["signals"][0]["kind"] == "channel_shift"


def test_remote_access_purchase_alone_not_flagged():
    # the software purchase alone, with no matching cash withdrawal, isn't enough
    txns = [_txn("t1", "GeekSquad Remote", "7379", "card_not_present", "299")]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is False
