"""Guardrail's pipeline routing.

Strands Graph was evaluated against strands-agents 1.52.0 (installed and read,
not guessed from docs) and is the right topology for this pipeline: the mermaid
diagram in the README *is* the graph. It is not what runs in production, and
the reason is narrower than "Graph can't do it":

Graph does forward each node's output to its successors. In 1.52.0,
`Graph._build_node_input` injects "Inputs from previous nodes: From monitor:
..." into every downstream prompt. What it forwards is the node's free-text
result. This pipeline needs two things Graph's edges don't give:

1. Each handoff must be exact JSON, not prose. A live Nova Pro run embedded a
   Python repr in a prompt and emitted malformed tool arguments that Bedrock
   rejected (see verifier.py for the fix). Typed pydantic contracts on every
   edge closed that class of bug; free-text edges reopen it.
2. Each gate must be unit-testable with no Bedrock call. `monitor_flagged`,
   `monitor_failed`, `verifier_corroborated` are plain functions, and
   tests/test_pipeline_stubbed.py drives the whole route with fake agents.

So the edges are the ~40 lines of Python below, and the nodes are unchanged
Strands Agents with @tool functions. If Graph grows typed edge payloads, the
nodes drop back in as-is. This is what app.py, run_local.py, and every test use.
"""

from guardrail.models import MonitorResult, VerifierResult

FAIL_OPEN_REASON = "schema_validation_failed"


def monitor_flagged(result: MonitorResult) -> bool:
    return result.flagged


def monitor_failed(result: MonitorResult) -> bool:
    """True when Monitor gave up (model/Bedrock failure), not when it found a signal."""
    return result.reasons == [FAIL_OPEN_REASON]


def verifier_corroborated(result: VerifierResult) -> bool:
    return result.corroborated


def fail_open_verdict() -> VerifierResult:
    return VerifierResult(
        corroborated=True, confidence=0.0, corroborating_signals=[], scam_pattern=FAIL_OPEN_REASON
    )


def run_pipeline(monitor_agent, verifier_agent, escalation_agent, account_id, actor_id, scenario, alert_id) -> dict:
    """Runs Monitor -> Verifier -> Escalation with the same gating rules as the
    Graph above, in plain Python. This is the actual source of truth."""
    from guardrail.agents.escalation import run_escalation
    from guardrail.agents.monitor import run_monitor
    from guardrail.agents.verifier import run_verifier
    from guardrail.memory.manager import record_trend_point
    from guardrail.synthetic.stream import get_transactions

    monitor_result = run_monitor(monitor_agent, account_id, actor_id, scenario)
    # Recorded regardless of outcome -- the trend view's entire point is showing
    # the quiet days too, not just the alerts.
    record_trend_point(actor_id, monitor_result, scenario)
    if not monitor_flagged(monitor_result):
        return {"status": "quiet", "monitor": monitor_result.model_dump()}

    if monitor_failed(monitor_result):
        # Fail OPEN, for real this time. Before this guard, Monitor's fallback
        # carried signals=[], cross_check_signals on an empty list returned
        # corroborated=False, and a Bedrock outage produced silence -- the
        # exact opposite of what the README promised. Reproduced with a
        # Monitor that raises 3x. Skipping the Verifier here is also the
        # right call on its own: there is nothing for it to corroborate, and
        # spending a model call to get a known-wrong answer is pure cost.
        verifier_result = fail_open_verdict()
    else:
        verifier_result = run_verifier(verifier_agent, monitor_result)
    if not verifier_corroborated(verifier_result):
        return {
            "status": "quiet_unverified",
            "monitor": monitor_result.model_dump(),
            "verifier": verifier_result.model_dump(),
        }

    alert = run_escalation(escalation_agent, verifier_result, actor_id, alert_id, get_transactions(scenario))
    return {
        "status": "escalated",
        "monitor": monitor_result.model_dump(),
        "verifier": verifier_result.model_dump(),
        "alert": alert.model_dump(),
    }
