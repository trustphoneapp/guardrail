import logging

from strands import Agent
from strands.models import BedrockModel

from guardrail.approval.token import issue_token
from guardrail.config import settings
from guardrail.models import Alert, Transaction, VerifierResult
from guardrail.tools.approval_tools import draft_alert, request_human_approval

logger = logging.getLogger(__name__)

ESCALATION_PROMPT = (
    "A scam signature has been independently corroborated. Call draft_alert to write "
    "a clear, non-alarmist message, then call request_human_approval so the family "
    "member can review and approve. You never send anything directly."
)


def build_escalation_agent(hooks=None, guard=None) -> Agent:
    return Agent(
        name="escalation",
        hooks=hooks,
        # The steering guard (guardrail.steering.EscalationGuard) pins
        # request_human_approval's alert_id/actor_id to the pipeline's own
        # values. Supervision, not prompting.
        plugins=[guard] if guard else None,
        model=BedrockModel(model_id=settings.bedrock_model_id, region_name=settings.aws_region),
        system_prompt=ESCALATION_PROMPT,
        tools=[draft_alert, request_human_approval],
    )


def run_escalation(
    agent: Agent, verifier_result: VerifierResult, actor_id: str, alert_id: str, evidence_trail: list[Transaction]
) -> Alert:
    for _ in range(3):
        try:
            agent(f"scam_pattern={verifier_result.scam_pattern} actor_id={actor_id} alert_id={alert_id}")
            break
        except Exception:
            logger.exception("run_escalation: agent tool-call loop failed")
    # ponytail: issue_token() is idempotent per alert_id (approval/token.py) — calling
    # it here guarantees a real, correctly-scoped token even if the agent's own
    # tool-call loop above didn't complete cleanly. Token issuance is never left to
    # the model's word for it; this line is the actual security boundary.
    token = issue_token(alert_id=alert_id, actor_id=actor_id)
    alert = Alert(
        alert_id=alert_id,
        actor_id=actor_id,
        verdict=verifier_result,
        evidence_trail=evidence_trail,
        approval_token=token,
        status="pending_approval",
    )
    # Persisted so the dashboard, a separate process, can show the real
    # evidence trail after the PIN. Before this, the post-PIN page was a
    # placeholder and the link from the live runtime returned 403.
    from guardrail.memory.manager import save_alert

    save_alert(alert)
    return alert
