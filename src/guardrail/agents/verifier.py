import json
import logging

from strands import Agent
from strands.models import BedrockModel

from guardrail.config import settings
from guardrail.models import MonitorResult, VerifierResult
from guardrail.tools.corroboration_tools import cross_check_signals

logger = logging.getLogger(__name__)

VERIFIER_PROMPT = (
    "You independently re-check a flagged deviation against known scam-pattern "
    "fingerprints. You MUST call cross_check_signals before answering. Report "
    "EXACTLY what it returned -- its corroborated/confidence/scam_pattern are "
    "deterministic and authoritative; do not paraphrase or override them."
)


def build_verifier_agent() -> Agent:
    return Agent(
        model=BedrockModel(model_id=settings.bedrock_model_id, region_name=settings.aws_region),
        system_prompt=VERIFIER_PROMPT,
        tools=[cross_check_signals],
    )


def run_verifier(agent: Agent, monitor_result: MonitorResult) -> VerifierResult:
    # See monitor.py's run_monitor for why this is agent(..., structured_output_model=)
    # and not the deprecated agent.structured_output() -- same confirmed bug,
    # same fix.
    #
    # json.dumps(), not an f-string of the list -- confirmed live in production
    # (CloudWatch logs, guardrail_agent runtime) that embedding Python's default
    # repr (single-quoted dict syntax) here caused Nova Pro to occasionally echo
    # malformed non-JSON text into a tool-call argument, which Bedrock's Converse
    # API then rejected outright: "messages.1.content.1.toolUse.input is invalid.
    # Provide a json object". Real JSON in the prompt removes the ambiguity.
    signals_json = json.dumps([s.model_dump(mode="json") for s in monitor_result.signals])
    prompt = f"signals={signals_json}. Call cross_check_signals, then report its result exactly."
    for _ in range(3):
        try:
            result = agent(prompt, structured_output_model=VerifierResult)
            return result.structured_output
        except Exception:
            logger.exception("run_verifier: structured_output attempt failed")
    # ponytail: fails open toward corroborated=True — same reasoning as Monitor.
    from guardrail.graph import fail_open_verdict

    return fail_open_verdict()
