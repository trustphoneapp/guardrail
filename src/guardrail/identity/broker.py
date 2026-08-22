class ActorMismatch(Exception):
    """Raised when a tool is asked to broker a credential for no/blank actor_id.
    In production this also fires when a workload token's bound actor doesn't
    match the requested actor — the one place a prompt-injected actor_id swap
    would actually matter."""


def get_plaid_sandbox_token(actor_id: str) -> str:
    """Stands in for AgentCore Identity's resource-token exchange
    (IdentityClient.get_resource_token(resource="plaid-sandbox", scopes=[...]),
    scoped to a workload access token bound to actor_id). No real secret lives
    here in the demo build — the placeholder is never returned to the model."""
    if not actor_id:
        raise ActorMismatch("actor_id required")
    return f"sandbox-token::{actor_id}"
