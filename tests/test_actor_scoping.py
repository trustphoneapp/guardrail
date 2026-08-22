import pytest

from guardrail.identity.broker import ActorMismatch, get_plaid_sandbox_token


def test_token_scoped_to_actor():
    tok = get_plaid_sandbox_token("actor-1")
    assert "actor-1" in tok


def test_empty_actor_raises():
    with pytest.raises(ActorMismatch):
        get_plaid_sandbox_token("")
