import logging

from strands import Agent
from strands.models import BedrockModel

from guardrail.config import settings

logger = logging.getLogger(__name__)
from guardrail.models import MonitorResult
from guardrail.tools.baseline_tools import get_behavioral_baseline, score_deviation
from guardrail.tools.plaid_tools import fetch_recent_transactions

MONITOR_PROMPT = (
    "You watch one elder's account for behavioral deviation from their baseline. "
    "You MUST call fetch_recent_transactions, then get_behavioral_baseline, then "
    "score_deviation, in that order, before answering. Report EXACTLY what "
    "score_deviation returned — its flagged/deviation_score/reasons/signals are "
    "deterministic and authoritative; do not paraphrase, summarize, or override "
    "them with your own judgment."
)


def build_monitor_agent() -> Agent:
    return Agent(
        model=BedrockModel(model_id=settings.bedrock_model_id, region_name=settings.aws_region),
        system_prompt=MONITOR_PROMPT,
        tools=[fetch_recent_transactions, get_behavioral_baseline, score_deviation],
    )


def run_monitor(agent: Agent, account_id: str, actor_id: str, scenario: str = "quiet_day") -> MonitorResult:
    # agent.structured_output() is deprecated AND was confirmed, live, to skip
    # the tool-calling loop entirely on some runs -- producing a flagged=False
    # guess with zero grounding in score_deviation's actual output. The
    # structured_output_model kwarg on a normal call reliably runs the full
    # tool loop and faithfully carries the tool's exact values through; verified
    # by inspecting agent.messages and diffing against score_deviation's raw
    # toolResult.
    prompt = (
        f"account_id={account_id} actor_id={actor_id} scenario={scenario}. "
        "Call fetch_recent_transactions, then get_behavioral_baseline, then "
        "score_deviation, then report score_deviation's result exactly."
    )
    for _ in range(3):
        try:
            result = agent(prompt, structured_output_model=MonitorResult)
            return result.structured_output
        except Exception:
            # A silently-swallowed exception here once hid a real
            # AccessDeniedException for 3 retries and masked it as a routine
            # schema-validation failure. Log it every time, not just on the
            # final give-up.
            logger.exception("run_monitor: structured_output attempt failed")
    # ponytail: schema failure fails OPEN to escalate — an undetected miss is worse
    # than a false positive a human dismisses.
    return MonitorResult(
        flagged=True, deviation_score=1.0, reasons=["schema_validation_failed"], signals=[], transaction_ids=[]
    )
