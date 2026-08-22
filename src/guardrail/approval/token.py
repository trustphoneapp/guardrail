import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timedelta

from guardrail.config import settings
from guardrail.models import ApprovalToken

# ponytail: in-memory store — correct for a single-process hackathon demo, not for
# multiple instances. Swap for DynamoDB per the architecture spec when the demo
# needs to survive a process restart or run behind more than one worker.
#
# All three dicts are keyed by token_id, not alert_id. alert_id is deterministic
# (app.py builds it from actor + scenario), so keying redemption by alert_id
# meant one approval killed every future token for that scenario. Found by a
# skeptical code read before a judge could.
_TOKENS: dict[str, ApprovalToken] = {}
_REDEEMED: set[str] = set()
_ATTEMPTS: dict[str, int] = {}
_BY_ALERT: dict[str, str] = {}  # alert_id -> current token_id

# FastAPI runs sync handlers in a threadpool, so two redeems of the same token
# can race. One lock around the check-and-mark is the whole fix.
_LOCK = threading.Lock()

MAX_PIN_ATTEMPTS = 5
TTL_MINUTES = 15
EXTENDED_TTL_MINUTES = 30


def _sign(alert_id: str, actor_id: str, nonce: str) -> str:
    msg = f"{alert_id}:{actor_id}:{nonce}".encode()
    return hmac.new(settings.approval_token_signing_key.encode(), msg, hashlib.sha256).hexdigest()


def _is_live(token: ApprovalToken) -> bool:
    return (
        token.expires_at > datetime.utcnow()
        and token.token_id not in _REDEEMED
        and _ATTEMPTS.get(token.token_id, 0) < MAX_PIN_ATTEMPTS
    )


def issue_token(alert_id: str, actor_id: str) -> ApprovalToken:
    """Idempotent per alert_id while the current token is live. Re-issuing for
    the same alert returns the existing token rather than minting a second one,
    which is what lets run_escalation() call it unconditionally after the
    agent's own tool-call loop without double-issuing. A redeemed, expired, or
    burned token is never handed back; a fresh one is minted instead."""
    with _LOCK:
        current_id = _BY_ALERT.get(alert_id)
        if current_id:
            existing = _TOKENS.get(current_id)
            if existing and _is_live(existing):
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
        _TOKENS[token.token_id] = token
        _ATTEMPTS[token.token_id] = 0
        _BY_ALERT[alert_id] = token.token_id
        return token


def extend_token(alert_id: str) -> ApprovalToken | None:
    """T+7min no-response resend: extends TTL to 30 minutes total from issuance.
    Refuses to extend a burned or redeemed token; that would resurrect it."""
    with _LOCK:
        current_id = _BY_ALERT.get(alert_id)
        token = _TOKENS.get(current_id) if current_id else None
        if token is None or token.token_id in _REDEEMED or _ATTEMPTS.get(token.token_id, 0) >= MAX_PIN_ATTEMPTS:
            return None
        token.expires_at = token.issued_at + timedelta(minutes=EXTENDED_TTL_MINUTES)
        return token


def redeem_token(token_id: str, pin_hash: str, expected_pin_hash: str) -> ApprovalToken:
    with _LOCK:
        token = _TOKENS.get(token_id)
        if token is None:
            raise ValueError("unknown token")
        if token_id in _REDEEMED:
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

        _REDEEMED.add(token_id)
        return token
