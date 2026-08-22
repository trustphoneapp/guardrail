"""AgentCore Runtime entrypoint — container deploy target.

Switched from direct-code-deploy (.zip) to container/ECR after checking AWS's
own current Strands deployment guide directly: its "AgentCore Runtime
Requirements Summary" states ECR is required, and both of its documented
deployment paths (SDK Integration, Custom Agent) only demonstrate container
images end-to-end. The zip-based codeConfiguration parameter exists in the raw
CreateAgentRuntime API but isn't demonstrated anywhere in that guide -- not
worth betting a deadline on reverse-engineering an undocumented shape when the
container path is fully documented and this machine is already Apple Silicon
(linux/arm64 natively, no cross-build risk).

Checked against bedrock-agentcore 1.22.0's real RequestContext
(runtime/context.py): it exposes `session_id` (a plain string) and
`request_headers`, and nothing else useful here — no `.session` sub-object, no
`actor_id` field. That earlier assumption was wrong, and it pointed at a real
design confusion, not just a naming miss: this entrypoint is invoked on a
SCHEDULE (EventBridge Scheduler -> AgentCore Runtime), not by a logged-in human,
so there is no "authenticated session" to pull an actor from in the first place.

The correct security boundary here is IAM, not session-vs-payload: AgentCore
Runtime's resource policy must restrict *who can invoke this endpoint* to our
own EventBridge Scheduler execution role. Given that, trusting `actor_id` from
the payload is fine — the payload is EventBridge's own fixed target input,
provisioned by us per elder at enrollment time, not attacker-influenceable.
(The "never trust actor_id from the caller" rule still applies, correctly, to
the dashboard's /approve/{token} flow in dashboard/server.py — that endpoint
*is* reachable by an arbitrary browser, and it never uses a payload actor_id at
all; the token itself is scoped to one actor.)
"""

from bedrock_agentcore import BedrockAgentCoreApp

from guardrail.agents.escalation import build_escalation_agent
from guardrail.agents.monitor import build_monitor_agent
from guardrail.agents.verifier import build_verifier_agent
from guardrail.config import settings
from guardrail.graph import run_pipeline

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    # Trusted because IAM restricts invocation to our own Scheduler role (see
    # module docstring) — this is EventBridge's fixed target input, not a
    # caller-supplied value from an open endpoint.
    actor_id = payload.get("actor_id") or settings.demo_actor_id
    account_id = payload.get("account_id", "acct-1")
    scenario = payload.get("scenario", "quiet_day")  # demo-only knob
    alert_id = f"alert-{actor_id}-{scenario}"

    from guardrail.audit import AuditTrail
    from guardrail.steering import EscalationGuard

    audit = AuditTrail()
    monitor = build_monitor_agent(hooks=[audit])
    verifier = build_verifier_agent(hooks=[audit])
    escalation = build_escalation_agent(hooks=[audit], guard=EscalationGuard(alert_id, actor_id))

    out = run_pipeline(monitor, verifier, escalation, account_id, actor_id, scenario, alert_id, audit=audit)
    if payload.get("debug"):
        # Which storage/notify config the container actually sees. Exists
        # because an AgentCore env-var update once showed in the runtime config
        # but not in the running container, and there was no way to tell from
        # outside. Only returned when the caller asks.
        import os

        out["debug"] = {
            "guardrail_table": os.environ.get("GUARDRAIL_TABLE"),
            "dashboard_url": os.environ.get("GUARDRAIL_DASHBOARD_URL"),
        }
    return out


if __name__ == "__main__":
    app.run()
