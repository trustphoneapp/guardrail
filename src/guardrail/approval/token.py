import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from guardrail.config import settings
from guardrail.models import ApprovalToken

# ponytail: in-memory store — correct for a single-process hackathon demo, not for
# multiple instances. Swap for SQLite/DynamoDB per the architecture spec when the
# demo needs to survive a process restart or run behind more than one worker.
_TOKENS: dict[str, ApprovalToken] = {}
_REDEEMED: set[str] = set()
_ATTEMPTS: dict[str, int] = {}

MAX_PIN_ATTEMPTS = 5
TTL_MINUTES = 15
EXTENDED_TTL_MINUTES = 30


def _sign(alert_id: str, actor_id: str, nonce: str) -> str:
    msg = f"{alert_id}:{actor_id}:{nonce}".encode()
    return hmac.new(settings.approval_token_signing_key.encode(), msg, hashlib.sha256).hexdigest()


def issue_token(alert_id: str, actor_id: str) -> ApprovalToken:
    """Idempotent per alert_id — re-issuing for the same alert returns the existing,
    still-valid token rather than minting a second one. This is what lets
    run_escalation() call it unconditionally after the agent's own tool-call loop,
    without ever double-issuing."""
    existing = _TOKENS.get(alert_id)
    if existing and existing.expires_at > datetime.utcnow() and existing.alert_id not in _REDEEMED:
        return existing

    nonce = secrets.token_hex(16)
    now = datetime.utcnow()
    token = ApprovalToken(
        token_id=secrets.token_urlsafe(24),
        alert_id=alert_id,
        actor_id=actor_id,
        scope="alert:approve_deny",
        issued_at=now,
        expires_at=now + timedelta(minutes=TTL_MINUTES),
        nonce=nonce,
        signature=_sign(alert_id, actor_id, nonce),
    )
    _TOKENS[alert_id] = token
    _ATTEMPTS[token.token_id] = 0
    return token


def extend_token(alert_id: str) -> ApprovalToken | None:
    """T+7min no-response resend: extends TTL to 30 minutes total from issuance."""
    token = _TOKENS.get(alert_id)
    if token is None:
        return None
    token.expires_at = token.issued_at + timedelta(minutes=EXTENDED_TTL_MINUTES)
    return token


def redeem_token(token_id: str, pin_hash: str, expected_pin_hash: str) -> ApprovalToken:
    token = next((t for t in _TOKENS.values() if t.token_id == token_id), None)
    if token is None:
        raise ValueError("unknown token")
    if token.alert_id in _REDEEMED:
        raise ValueError("token already used")
    if token.expires_at < datetime.utcnow():
        raise ValueError("token expired")
    if not hmac.compare_digest(token.signature, _sign(token.alert_id, token.actor_id, token.nonce)):
        raise ValueError("bad signature")
    if _ATTEMPTS[token_id] >= MAX_PIN_ATTEMPTS:
        raise ValueError("token burned — too many failed PIN attempts")

    if not hmac.compare_digest(pin_hash, expected_pin_hash):
        _ATTEMPTS[token_id] += 1
        remaining = MAX_PIN_ATTEMPTS - _ATTEMPTS[token_id]
        raise ValueError(f"wrong PIN, {remaining} attempts remaining")

    _REDEEMED.add(token.alert_id)
    return token
