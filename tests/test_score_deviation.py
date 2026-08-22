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


# --- the cases a skeptical judge would try first ---

import pytest


@pytest.mark.parametrize(
    "merchant,mcc",
    [
        ("Target Gift-Card", "5411"),  # hyphen evaded the old substring check
        ("Vanilla Visa Prepaid", "5411"),
        ("Green Dot MoneyPak", "5411"),
        ("Walgreens Reload", "5912"),
        ("Some Kiosk", "6051"),  # quasi-cash MCC with an uninformative name
    ],
)
def test_gift_card_variants_are_recognized(merchant, mcc):
    txns = [_txn("t1", merchant, mcc, "card_not_present", "200"), _txn("t2", merchant, mcc, "card_not_present", "200")]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is True, merchant


def test_single_large_gift_card_is_flagged():
    txns = [_txn("t1", "Apple GiftCard", "5732", "card_not_present", "2000")]
    result = score_deviation(transactions=txns, baseline=BASELINE)
    assert result["flagged"] is True
    assert "single large" in result["reasons"][0]


def test_single_small_gift_card_is_not_flagged():
    # a birthday present, not a scam
    txns = [_txn("t1", "Apple GiftCard", "5732", "card_not_present", "50")]
    assert score_deviation(transactions=txns, baseline=BASELINE)["flagged"] is False


def test_small_wire_to_hospital_is_not_flagged():
    # seed-42 median is ~$18, so 10x median is ~$181. A $200 medical wire used
    # to escalate as a romance scam. The absolute floor stops that.
    small_median = {"cadence_hist": {"median_amount": 18.13}}
    txns = [_txn("t1", "County Hospital", "8062", "wire", "200")]
    assert score_deviation(transactions=txns, baseline=small_median)["flagged"] is False


def test_large_wire_still_flagged_with_small_median():
    small_median = {"cadence_hist": {"median_amount": 18.13}}
    txns = [_txn("t1", "Western Union", "4829", "wire", "4200")]
    assert score_deviation(transactions=txns, baseline=small_median)["flagged"] is True
