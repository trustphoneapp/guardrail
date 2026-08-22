from strands import tool

from guardrail.identity.broker import get_plaid_sandbox_token
from guardrail.synthetic.stream import get_transactions


@tool
def fetch_recent_transactions(account_id: str, actor_id: str, scenario: str = "quiet_day") -> list[dict]:
    """Fetch transactions from the Plaid Sandbox interface. In the hackathon build
    this reads a labeled synthetic/scenario stream, never real bank data. `scenario`
    is a demo-only knob — production never lets the caller choose the data source."""
    get_plaid_sandbox_token(actor_id)  # brokered token pulled and discarded, never returned to the model
    return [t.model_dump(mode="json") for t in get_transactions(scenario)]
