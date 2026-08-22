"""Lambda relay between EventBridge Scheduler and the AgentCore runtime.

Why this exists: the schedule originally targeted
arn:aws:scheduler:::aws-sdk:bedrockagentcore:invokeAgentRuntime directly, and
every fire errored and was dropped without a retry -- the signature of a
non-retryable client error. InvokeAgentRuntime has a streaming response,
which EventBridge Scheduler's universal targets don't support, and the
universal target also can't mint a fresh session ID per fire (AgentCore
sessions expire, so a fixed ID goes stale). A five-line Lambda solves both:
Scheduler -> Lambda is a plain templated target, and boto3 handles the
streaming response and a uuid per run.
"""

import json
import os
import uuid

import boto3

RUNTIME_ARN = os.environ["GUARDRAIL_RUNTIME_ARN"]


def handler(event, context):
    payload = {
        "actor_id": event.get("actor_id", "sarla-demo-001"),
        "account_id": event.get("account_id", "acct-1"),
        "scenario": event.get("scenario", "quiet_day"),
    }
    client = boto3.client("bedrock-agentcore")
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=f"guardrail-sched-{uuid.uuid4()}",
        payload=json.dumps(payload).encode(),
    )
    body = resp["response"].read().decode()
    print(f"[guardrail-scheduler] scenario={payload['scenario']} -> {body[:200]}")
    return {"statusCode": resp["statusCode"], "head": body[:200]}
