"""Guardrail's pipeline routing.

The Day-1 spike is DONE — checked against strands-agents 1.52.0, installed and
introspected directly, not guessed from docs. Two findings, one fixable, one that
changed the design:

1. GraphBuilder.add_node/add_edge/set_entry_point all match what an earlier draft
   of this file assumed — except node output isn't read via a `.get_output()`
   method (that doesn't exist); it's `NodeResult.get_agent_results()[0].structured_output`.
2. The real problem: `Graph.__call__(task, ...)` takes ONE shared task for the
   whole run. It doesn't give each node a distinct, code-constructed prompt built
   from the previous node's typed output — but that's exactly what this pipeline
   needs (Verifier must see Monitor's specific signals; Escalation must see
   Verifier's specific scam_pattern). Strands' `Graph` object is built for
   task/context propagation between agents, not for chaining typed,
   deterministically-constructed inter-node calls.

So `Graph` is dropped for the deployed pipeline. `run_pipeline()` below — plain
Python, explicit per-node prompts, each gated on the previous node's structured
result — already delivers the "deterministic, auditable, explain why this fired"
story the Graph primitive was chosen for, with less framework to fight. This is
what app.py, run_local.py, and every test actually use.
"""

from guardrail.models import MonitorResult, VerifierResult


def monitor_flagged(result: MonitorResult) -> bool:
    return result.flagged


def verifier_corroborated(result: VerifierResult) -> bool:
    return result.corroborated


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
