import hashlib

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from guardrail.approval.token import redeem_token
from guardrail.memory.manager import get_alert, get_trend

app = FastAPI(title="Guardrail Dashboard")


def _pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# MVP: one demo PIN. Production stores a per-actor salted hash set at enrollment.
_DEMO_PIN_HASH = _pin_hash("000000")


@app.get("/approve/{token_id}", response_class=HTMLResponse)
def approve_stub(token_id: str) -> str:
    """Redacted stub: zero transaction data pre-auth, and no name either. The
    page is reachable by anyone holding the link; the elder's identity is part
    of what the PIN protects."""
    return f"""<html><body>
<h1>Possible unusual activity on a watched account</h1>
<form method="post" action="/approve/{token_id}">
<label>Enter your PIN: <input type="password" name="pin" autofocus></label>
<button type="submit">View details</button>
</form>
</body></html>"""


@app.post("/approve/{token_id}", response_class=HTMLResponse)
def approve_full(token_id: str, pin: str = Form(...)) -> str:
    try:
        token = redeem_token(token_id, _pin_hash(pin), _DEMO_PIN_HASH)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    alert = get_alert(token.alert_id)
    if alert is None:
        # Token was valid but the alert body is gone (store reset). Say so
        # rather than render an empty trail as if nothing happened.
        return "<html><body><h1>Verified, but the alert details are no longer available.</h1></body></html>"

    rows = "\n".join(
        f"<tr><td>{t.ts.isoformat(timespec='minutes')}</td><td>{t.merchant_name}</td>"
        f"<td>{t.channel}</td><td>${t.amount}</td></tr>"
        for t in alert.evidence_trail
    )
    reasons = ", ".join(alert.verdict.corroborating_signals and [s.kind for s in alert.verdict.corroborating_signals] or ["model failure, failed open"])
    return f"""<html><body>
<h1>Why Guardrail flagged this</h1>
<p><b>Pattern:</b> {alert.verdict.scam_pattern} &nbsp; <b>Confidence:</b> {alert.verdict.confidence:.2f} &nbsp; <b>Signals:</b> {reasons}</p>
<table border="1" cellpadding="6">
<tr><th>When</th><th>Merchant</th><th>Channel</th><th>Amount</th></tr>
{rows}
</table>
<p>Nothing has been sent, frozen, or moved. This page is the only action Guardrail takes.</p>
<form method="post" action="/decide/{alert.alert_id}">
<button name="decision" value="approve">This looks wrong, call Mom</button>
<button name="decision" value="dismiss">This was Mom, dismiss</button>
</form>
</body></html>"""


@app.post("/decide/{alert_id}", response_class=HTMLResponse)
def decide(alert_id: str, decision: str = Form(...)) -> str:
    """Records the family's decision. No bank action is taken either way; the
    only effect is on the alert's status and, on dismiss, the next run."""
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="unknown alert")
    if decision not in ("approve", "dismiss"):
        raise HTTPException(status_code=400, detail="decision must be approve or dismiss")
    from guardrail.memory.manager import add_to_allowlist, save_alert

    alert.status = "approved" if decision == "approve" else "denied"
    save_alert(alert)
    note = ""
    if decision == "dismiss":
        merchants = sorted({t.merchant_name for t in alert.evidence_trail})
        add_to_allowlist(alert.actor_id, merchants)
        note = f"<p>Added to the baseline as normal for this account: {', '.join(merchants)}. The next run will treat them as hers.</p>"
    return f"<html><body><h1>Recorded: {alert.status}</h1><p>Alert {alert_id}.</p>{note}</body></html>"


@app.get("/trend/{actor_id}", response_class=HTMLResponse)
def trend(actor_id: str) -> str:
    """Read-only, aggregate only -- deviation score and flagged/not, no
    transaction detail -- so this doesn't need the PIN gate /approve does.
    Production would still sit this behind Priya's own session; the hackathon
    build skips that since nothing sensitive renders here."""
    points = get_trend(actor_id)
    if not points:
        return "<html><body><h1>No runs yet</h1><p>Nothing recorded for this account.</p></body></html>"
    def _audit_cell(p) -> str:
        if not p.audit:
            return ""
        lines = "".join(
            f"<li>{e.get('agent')}: <code>{e.get('tool')}</code> "
            f"({e.get('duration_ms')}ms, {'ok' if e.get('ok') else 'FAILED'})</li>"
            for e in p.audit
        )
        return f"<details><summary>{len(p.audit)} tool calls</summary><ul>{lines}</ul></details>"

    rows = "\n".join(
        f"<tr><td>{p.ts.isoformat(timespec='minutes')}</td><td>{p.scenario}</td>"
        f"<td>{'flagged' if p.flagged else 'quiet'}</td><td>{p.deviation_score:.2f}</td>"
        f"<td>{_audit_cell(p)}</td></tr>"
        for p in reversed(points)
    )
    return f"""<html><body>
<h1>Guardrail — {actor_id}</h1>
<p>{len(points)} check{"s" if len(points) != 1 else ""} recorded. Silence on most days is the system working, not the system being idle.</p>
<table border="1" cellpadding="6">
<tr><th>Time</th><th>Scenario</th><th>Result</th><th>Deviation score</th><th>Why (audit trail)</th></tr>
{rows}
</table>
</body></html>"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
