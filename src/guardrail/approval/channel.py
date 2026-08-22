import os


def approval_url(token_id: str) -> str:
    """The public dashboard base comes from GUARDRAIL_DASHBOARD_URL so the
    runtime container emits a link that actually resolves. Falls back to a
    placeholder domain for local runs."""
    base = os.environ.get("GUARDRAIL_DASHBOARD_URL", "https://guardrail.example").rstrip("/")
    return f"{base}/approve/{token_id}"


def notify(actor_id: str, alert_id: str, token_id: str) -> None:
    """Sends only a magic link, never a code or PIN, over SMS/email. MVP: logs
    the would-be send instead of calling SNS, per the architecture's explicit
    cut. Swap the body for an SNS publish; the link shape doesn't change."""
    print(f"[guardrail] would notify actor={actor_id} alert={alert_id}: {approval_url(token_id)}")
