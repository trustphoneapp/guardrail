import hashlib

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from guardrail.approval.token import redeem_token
from guardrail.memory.manager import get_trend

app = FastAPI(title="Guardrail Dashboard")


def _pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# MVP: one demo PIN. Production stores a per-actor salted hash set at enrollment.
_DEMO_PIN_HASH = _pin_hash("000000")


@app.get("/approve/{token_id}", response_class=HTMLResponse)
def approve_stub(token_id: str) -> str:
    """Redacted stub — zero transaction data pre-auth."""
    return f"""<html><body>
<h1>Possible unusual activity on Sarla's account</h1>
<form method="post" action="/approve/{token_id}">
<label>Enter your PIN: <input type="password" name="pin"></label>
<button type="submit">View details</button>
</form>
</body></html>"""


@app.post("/approve/{token_id}", response_class=HTMLResponse)
def approve_full(token_id: str, pin: str = Form(...)) -> str:
    try:
        token = redeem_token(token_id, _pin_hash(pin), _DEMO_PIN_HASH)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return f"""<html><body>
<h1>Evidence trail — alert {token.alert_id}</h1>
<p>Token verified. Full transaction detail renders here.</p>
</body></html>"""


@app.get("/trend/{actor_id}", response_class=HTMLResponse)
def trend(actor_id: str) -> str:
    """Read-only, aggregate only -- deviation score and flagged/not, no
    transaction detail -- so this doesn't need the PIN gate /approve does.
    Production would still sit this behind Priya's own session; the hackathon
    build skips that since nothing sensitive renders here."""
    points = get_trend(actor_id)
    if not points:
        return "<html><body><h1>No runs yet</h1><p>Nothing recorded for this account.</p></body></html>"
    rows = "\n".join(
        f"<tr><td>{p.ts.isoformat(timespec='minutes')}</td><td>{p.scenario}</td>"
        f"<td>{'flagged' if p.flagged else 'quiet'}</td><td>{p.deviation_score:.2f}</td></tr>"
        for p in reversed(points)
    )
    return f"""<html><body>
<h1>Guardrail — {actor_id}</h1>
<p>{len(points)} check{"s" if len(points) != 1 else ""} recorded. Silence on most days is the system working, not the system being idle.</p>
<table border="1" cellpadding="6">
<tr><th>Time</th><th>Scenario</th><th>Result</th><th>Deviation score</th></tr>
{rows}
</table>
</body></html>"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
