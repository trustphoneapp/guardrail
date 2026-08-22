import hashlib

import pytest

from guardrail.approval.token import issue_token, redeem_token


def _pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def test_issue_is_idempotent_per_alert():
    t1 = issue_token(alert_id="a1", actor_id="actor1")
    t2 = issue_token(alert_id="a1", actor_id="actor1")
    assert t1.token_id == t2.token_id


def test_redeem_succeeds_with_correct_pin():
    token = issue_token(alert_id="a2", actor_id="actor1")
    result = redeem_token(token.token_id, _pin_hash("1234"), _pin_hash("1234"))
    assert result.token_id == token.token_id


def test_redeem_fails_with_wrong_pin():
    token = issue_token(alert_id="a3", actor_id="actor1")
    with pytest.raises(ValueError, match="wrong PIN"):
        redeem_token(token.token_id, _pin_hash("0000"), _pin_hash("1234"))


def test_token_burns_after_max_attempts():
    token = issue_token(alert_id="a4", actor_id="actor1")
    for _ in range(5):
        with pytest.raises(ValueError):
            redeem_token(token.token_id, _pin_hash("wrong"), _pin_hash("1234"))
    with pytest.raises(ValueError, match="burned"):
        redeem_token(token.token_id, _pin_hash("1234"), _pin_hash("1234"))


def test_single_use():
    token = issue_token(alert_id="a5", actor_id="actor1")
    redeem_token(token.token_id, _pin_hash("1234"), _pin_hash("1234"))
    with pytest.raises(ValueError, match="already used"):
        redeem_token(token.token_id, _pin_hash("1234"), _pin_hash("1234"))


def test_unknown_token_rejected():
    with pytest.raises(ValueError, match="unknown token"):
        redeem_token("not-a-real-token", _pin_hash("1234"), _pin_hash("1234"))
