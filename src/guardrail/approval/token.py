import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timedelta

from guardrail import store
from guardrail.config import settings
from guardrail.models import ApprovalToken

# Everything keyed by token_id, not alert_id. alert_id is deterministic
# (app.py builds it from actor + scenario), so keying redemption by alert_id
# meant one approval killed every future token for that scenario.
#
# Storage is guardrail.store: a dict in tests, DynamoDB when GUARDRAIL_TABLE is
# set. Single-use is an atomic put_if_absent on REDEEMED#<token_id>, which
# holds across the runtime container and the dashboard process. The lock below
# covers the in-process case and the read-modify-write on attempts.
_LOCK = threading.Lock()

MAX_PIN_ATTEMPTS = 5
TTL_MINUTES = 15
EXTENDED_TTL_MINUTES = 30

_TOKEN = "TOKEN"
_ALERT = "ALERT"
_REDEEMED = "REDEEMED"
_ATTEMPTS = "ATTEMPTS"


def _sign(alert_id: str, actor_id: str, nonce: str) -> str:
    msg = f"{alert_id}:{actor_id}:{nonce}".encode()
    return hmac.new(settings.approval_token_signing_key.encode(), msg, hashlib.sha256).hexdigest()


def _load(token_id: str) -> ApprovalToken | None:
    raw = store.get(_TOKEN, token_id)
    return ApprovalToken(**raw) if raw else None


def _save(token: ApprovalToken) -> None:
    store.put(_TOKEN, token.token_id, token.model_dump(mode="json"))


def _attempts(token_id: str) -> int:
    raw = store.get(_ATTEMPTS, token_id)
    return int(raw["n"]) if raw else 0


def _is_redeemed(token_id: str) -> bool:
    return store.get(_REDEEMED, token_id) is not None


def _is_live(token: ApprovalToken) -> bool:
    return (
        token.expires_at > datetime.utcnow()
        and not _is_redeemed(token.token_id)
        and _attempts(token.token_id) < MAX_PIN_ATTEMPTS
    )


def issue_token(alert_id: str, actor_id: str) -> ApprovalToken:
    """Idempotent per alert_id while the current token is live. A redeemed,
    expired, or burned token is never handed back; a fresh one is minted."""
    with _LOCK:
        current = store.get(_ALERT, alert_id)
        if current:
            existing = _load(current["token_id"])
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
        _save(token)
        store.put(_ATTEMPTS, token.token_id, {"n": 0})
        store.put(_ALERT, alert_id, {"token_id": token.token_id})
        return token


def extend_token(alert_id: str) -> ApprovalToken | None:
    """T+7min no-response resend: extends TTL to 30 minutes from issuance.
    Refuses to extend a burned or redeemed token; that would resurrect it."""
    with _LOCK:
        current = store.get(_ALERT, alert_id)
        token = _load(current["token_id"]) if current else None
        if token is None or _is_redeemed(token.token_id) or _attempts(token.token_id) >= MAX_PIN_ATTEMPTS:
            return None
        token.expires_at = token.issued_at + timedelta(minutes=EXTENDED_TTL_MINUTES)
        _save(token)
        return token


def redeem_token(token_id: str, pin_hash: str, expected_pin_hash: str) -> ApprovalToken:
    with _LOCK:
        token = _load(token_id)
        if token is None:
            raise ValueError("unknown token")
        if _is_redeemed(token_id):
            raise ValueError("token already used")
        if token.expires_at < datetime.utcnow():
            raise ValueError("token expired")
        if not hmac.compare_digest(token.signature, _sign(token.alert_id, token.actor_id, token.nonce)):
            raise ValueError("bad signature")
        n = _attempts(token_id)
        if n >= MAX_PIN_ATTEMPTS:
            raise ValueError("token burned — too many failed PIN attempts")

        if not hmac.compare_digest(pin_hash, expected_pin_hash):
            n += 1
            store.put(_ATTEMPTS, token_id, {"n": n})
            raise ValueError(f"wrong PIN, {MAX_PIN_ATTEMPTS - n} attempts remaining")

        # The atomic create is the single-use guarantee across processes.
        if not store.put_if_absent(_REDEEMED, token_id, {"at": datetime.utcnow().isoformat()}):
            raise ValueError("token already used")
        return token
