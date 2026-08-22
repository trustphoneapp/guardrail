"""Steering guard for the Escalation agent.

Prompting gives instruction; steering adds supervision. request_human_approval
mints a token and notifies using the alert_id and actor_id the MODEL passes as
tool arguments. Before this guard, a hallucinated or prompt-injected actor_id
would have sent the approval link to the wrong family, and run_escalation's
Python re-issue afterward would not un-send it. The guard pins both arguments
to the values the pipeline actually computed: any mismatch turns the tool call
into a Guide telling the model to use the real ones, and the call never runs.

This is Strands' vended steering plugin (strands.vended_plugins.steering), not
a prompt asking the model to behave.
"""

from typing import Any

from strands.vended_plugins.steering import Guide, Proceed, SteeringHandler


class EscalationGuard(SteeringHandler):
    def __init__(self, alert_id: str, actor_id: str) -> None:
        super().__init__()
        self.alert_id = alert_id
        self.actor_id = actor_id

    def steer_before_tool(self, *, agent: Any, tool_use: dict, **kwargs: Any):
        if tool_use.get("name") != "request_human_approval":
            return Proceed(reason="not the guarded tool")
        args = tool_use.get("input", {})
        if args.get("alert_id") != self.alert_id or args.get("actor_id") != self.actor_id:
            return Guide(
                reason=(
                    f"request_human_approval must be called with alert_id={self.alert_id!r} "
                    f"and actor_id={self.actor_id!r}, the values this pipeline run computed. "
                    "You passed different ones; call it again with exactly these."
                )
            )
        return Proceed(reason="alert_id and actor_id match the pipeline run")
