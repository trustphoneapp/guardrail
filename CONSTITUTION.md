# The Guardrail constitution

The rules this build is not allowed to break. Each one is enforced in code,
not in a prompt, and each names the file that enforces it. If a rule and the
code ever disagree, the code is wrong.

## 1. The model never touches money

No tool anywhere in the codebase can move, freeze, or spend funds. The only
bank-facing scope requested is read-only transactions. There is nothing for a
compromised or hallucinating agent to escalate INTO.

Enforced by: the tool surface itself — grep `@tool` across
[src/guardrail/tools/](src/guardrail/tools/); every tool reads or drafts,
none writes to an account.

## 2. The model never sends

`send_alert` does not exist as an agent tool. Notification and approval-token
minting are plain Python that runs after the agent loop, whether or not the
model behaved. An agent that never calls `request_human_approval` still
produces a valid, correctly-scoped token.

Enforced by: [src/guardrail/agents/escalation.py](src/guardrail/agents/escalation.py)
(`issue_token` called unconditionally outside the agent loop);
[src/guardrail/approval/token.py](src/guardrail/approval/token.py) (HMAC
signing key never enters the model's context).

## 3. The model never does the math

Every flag/no-flag decision is a deterministic rule over transactions and the
elder's own baseline. The model's job is orchestration and plain-language
explanation. A faithfulness guard recomputes the rules after the Monitor
answers and overrides the model on any mismatch.

Enforced by: [src/guardrail/tools/baseline_tools.py](src/guardrail/tools/baseline_tools.py)
(`score_deviation`), the guard in
[src/guardrail/agents/monitor.py](src/guardrail/agents/monitor.py), and
[tests/test_score_deviation.py](tests/test_score_deviation.py).

## 4. Failure wakes a human, never silence

If the Monitor or Verifier crashes outright (Bedrock down, schema failure
after retries), the pipeline escalates instead of going quiet. An undetected
miss is worse than a false alarm a human dismisses in thirty seconds.

Enforced by: `monitor_failed` / `fail_open_verdict` in
[src/guardrail/graph.py](src/guardrail/graph.py);
`test_monitor_outage_fails_open_to_a_human` in
[tests/test_pipeline_stubbed.py](tests/test_pipeline_stubbed.py).

## 5. The model cannot choose who gets told

A Strands Steering guard sits in front of the Escalation agent's tools: a
tool call whose `alert_id`/`actor_id` differ from the pipeline's own values is
refused before it executes. A prompt-injected or hallucinated actor cannot
route an approval link to a different family.

Enforced by: the steering handler in
[src/guardrail/agents/escalation.py](src/guardrail/agents/escalation.py) and
its unit tests.

## 6. One approval, one human, one use

Approval tokens are HMAC-signed, single-use, 15-minute, scoped to one alert
for one actor, and burn after five wrong PINs. Redemption is an atomic
conditional write, so two simultaneous clicks cannot both succeed — verified
across separate OS processes, not just threads.

Enforced by: [src/guardrail/approval/token.py](src/guardrail/approval/token.py);
[tests/test_approval_tokens.py](tests/test_approval_tokens.py).

## 7. Silence is an outcome, not an absence

Every run is recorded, quiet or flagged, with its tool-call audit trail. The
trend page shows the quiet days on purpose: a watchdog you cannot see working
is indistinguishable from one that is broken.

Enforced by: `record_trend_point` in
[src/guardrail/memory/manager.py](src/guardrail/memory/manager.py); the
audit HookProvider; `/trend/{actor_id}` in
[src/guardrail/dashboard/server.py](src/guardrail/dashboard/server.py).

## What the humans owe in return

Honest labeling. The transaction stream is Plaid-shaped synthetic data and
says so; the demo PIN is a demo PIN; every "this would be real in production"
seam is named in the README rather than blurred. The constitution binds the
authors too.
