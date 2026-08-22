from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class Transaction(BaseModel):
    account_id: str
    txn_id: str
    ts: datetime
    amount: Decimal
    merchant_name: str
    mcc: str
    channel: Literal["card_present", "card_not_present", "ach", "wire", "p2p", "atm"]


class BaselineProfile(BaseModel):
    actor_id: str
    mcc_distribution: dict[str, float]
    cadence_hist: dict[str, float]
    seasonal_drift: dict[str, float]
    updated_at: datetime
    # Merchants the family has explicitly said are fine ("This was Mom").
    # score_deviation skips them, so a dismissal changes the next run: the
    # human decision closes the loop instead of vanishing into a log.
    allowlist: list[str] = []


class Signal(BaseModel):
    kind: Literal[
        "cadence_break", "new_payee_high_value", "mcc_anomaly", "channel_shift", "velocity_spike"
    ]
    severity: float
    evidence: dict


class MonitorResult(BaseModel):
    flagged: bool
    deviation_score: float
    reasons: list[str]
    signals: list[Signal]
    transaction_ids: list[str]


class VerifierResult(BaseModel):
    corroborated: bool
    confidence: float
    corroborating_signals: list[Signal]
    scam_pattern: str | None = None
    # Features the Verifier found that Monitor's rules never examined
    # (round_amounts, tight_window, unfamiliar_category). Corroboration
    # requires at least one; this is what makes the second check independent
    # rather than a restatement.
    independent_features: list[str] = []


class ApprovalToken(BaseModel):
    token_id: str
    alert_id: str
    actor_id: str
    scope: Literal["alert:approve_deny"]
    issued_at: datetime
    expires_at: datetime
    nonce: str
    signature: str


class TrendPoint(BaseModel):
    ts: datetime
    actor_id: str
    scenario: str
    flagged: bool
    deviation_score: float
    # Every tool call the agents made during this run, recorded by hooks
    # (audit.py): agent, tool, duration_ms, ok, one-line summary.
    audit: list[dict] = []


class Alert(BaseModel):
    alert_id: str
    actor_id: str
    verdict: VerifierResult
    evidence_trail: list[Transaction]
    approval_token: ApprovalToken
    status: Literal["pending_approval", "approved", "denied", "expired"] = "pending_approval"
