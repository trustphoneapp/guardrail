from guardrail.models import Transaction
from guardrail.synthetic.scenarios import SCENARIOS


def get_transactions(scenario_key: str = "quiet_day") -> list[Transaction]:
    """Stands in for the Plaid Sandbox interface — labeled synthetic, never real
    bank data. Raises on an unknown key rather than silently falling back."""
    scenario = SCENARIOS.get(scenario_key)
    if scenario is None:
        raise KeyError(f"Unknown scenario '{scenario_key}'. Known: {list(SCENARIOS)}")
    return scenario["transactions"]
