from strands import tool

from guardrail.approval.channel import notify
from guardrail.approval.token import issue_token


@tool
def draft_alert(scam_pattern: str, actor_id: str) -> dict:
    """Compose a human-readable alert draft. Does not send anything."""
    pattern = scam_pattern or "unusual activity"
    message = (
        f"Possible unusual activity on the watched account: pattern matches '{pattern}'. "
        f"Tap the link to review and approve or dismiss."
    )
    return {"draft_message": message}


@tool
def request_human_approval(alert_id: str, actor_id: str, draft_message: str) -> dict:
    """Issues a signed, single-use, scoped approval token server-side and notifies
    the approval channel with only a link — never a code or PIN. The model never
    sees the signing key or a valid token."""
    token = issue_token(alert_id=alert_id, actor_id=actor_id)
    notify(actor_id=actor_id, alert_id=alert_id, token_id=token.token_id)
    return {"alert_id": alert_id, "status": "pending_approval"}
