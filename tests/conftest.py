import pytest

from guardrail import store


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch):
    # Every test gets an empty in-process store and is guaranteed to never
    # touch DynamoDB, even if the developer's shell has GUARDRAIL_TABLE set.
    monkeypatch.delenv("GUARDRAIL_TABLE", raising=False)
    store.reset_for_tests()
    yield
    store.reset_for_tests()
