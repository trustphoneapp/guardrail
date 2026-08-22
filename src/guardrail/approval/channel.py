def notify(actor_id: str, alert_id: str, token_id: str) -> None:
    """Sends only a magic link — never a code or PIN — over SMS/email. MVP: logs
    the would-be send instead of calling SNS, per the architecture's explicit cut.
    Swap the body for an SNS publish call; the link shape doesn't change."""
    link = f"https://guardrail.example/approve/{token_id}"
    print(f"[guardrail] would notify actor={actor_id} alert={alert_id}: {link}")
