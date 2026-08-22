"""Runs the pipeline against one scenario against a real Bedrock-backed agent — needs
AWS credentials for the LLM calls, but not for the routing logic itself (see
tests/test_graph_routing.py for that in isolation)."""

import argparse

from guardrail.agents.escalation import build_escalation_agent
from guardrail.agents.monitor import build_monitor_agent
from guardrail.agents.verifier import build_verifier_agent
from guardrail.graph import run_pipeline
from guardrail.memory.manager import seed_baseline
from guardrail.synthetic.scenarios import SCENARIOS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="quiet_day", choices=list(SCENARIOS))
    parser.add_argument("--actor-id", default="sarla-demo-001")
    parser.add_argument("--account-id", default="acct-1")
    args = parser.parse_args()

    from guardrail.audit import AuditTrail
    from guardrail.steering import EscalationGuard

    seed_baseline(args.actor_id)
    alert_id = f"alert-{args.actor_id}-{args.scenario}"
    audit = AuditTrail()
    monitor = build_monitor_agent(hooks=[audit])
    verifier = build_verifier_agent(hooks=[audit])
    escalation = build_escalation_agent(hooks=[audit], guard=EscalationGuard(alert_id, args.actor_id))

    result = run_pipeline(
        monitor,
        verifier,
        escalation,
        account_id=args.account_id,
        actor_id=args.actor_id,
        scenario=args.scenario,
        alert_id=alert_id,
        audit=audit,
    )
    print(result)


if __name__ == "__main__":
    main()
