"""One-time setup: creates the EventBridge Scheduler role and the daily
schedule that invokes the deployed Guardrail agent. Run once after the
AgentCore Runtime exists; re-running is safe (create calls fail loudly if the
role/schedule already exist rather than silently duplicating).
"""

import base64
import json

import boto3

ACCOUNT_ID = "156470788861"
REGION = "us-east-1"
RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:runtime/guardrail_agent-oO0Y9nFhQs"
ROLE_NAME = "AmazonBedrockAgentCoreGuardrailSchedulerRole"


def main():
    iam = boto3.client("iam", region_name=REGION)
    scheduler = boto3.client("scheduler", region_name=REGION)

    with open("infra/iam/scheduler_role_trust.json") as f:
        trust_policy = f.read()
    with open("infra/iam/scheduler_role_policy.json") as f:
        permissions_policy = f.read()

    role = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=trust_policy,
        Description="EventBridge Scheduler role -- invokes the Guardrail AgentCore runtime on a schedule, nothing else",
        Tags=[{"Key": "Project", "Value": "guardrail"}, {"Key": "ManagedBy", "Value": "setup_scheduler.py"}],
    )
    role_arn = role["Role"]["Arn"]
    print(f"Created role: {role_arn}")

    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="InvokeGuardrailRuntimeOnly",
        PolicyDocument=permissions_policy,
    )
    print("Attached invoke-only policy")

    # ponytail: daily cadence for the demo. Real production monitoring
    # frequency (hourly, every 15 min) is a config change, not a design
    # change -- add when the hackathon demo needs to show a tighter loop.
    schedule = scheduler.create_schedule(
        Name="guardrail-daily-check",
        ScheduleExpression="rate(1 day)",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            # "bedrockagentcore", not "bedrock-agentcore" -- confirmed live.
            # Scheduler's universal target service identifier is the SDK's
            # serviceId lowercased/despaced ("Bedrock AgentCore" -> "bedrockagentcore"),
            # not the boto3 client name or endpoint prefix (both "bedrock-agentcore").
            # Checked directly against botocore's service model, not guessed --
            # the hyphenated form fails with "the api ... is not valid for the
            # service aws-sdk:bedrock-agentcore".
            "Arn": "arn:aws:scheduler:::aws-sdk:bedrockagentcore:invokeAgentRuntime",
            "RoleArn": role_arn,
            "Input": json.dumps(
                {
                    "AgentRuntimeArn": RUNTIME_ARN,
                    "RuntimeSessionId": "guardrail-scheduled-run-" + "0" * 20,  # AgentCore requires 33+ chars
                    # Payload is a blob param -- AWS JSON protocols represent
                    # blobs as base64 in the request, not raw bytes/latin1.
                    "Payload": base64.b64encode(
                        json.dumps({"actor_id": "sarla-demo-001", "account_id": "acct-1", "scenario": "quiet_day"}).encode()
                    ).decode("ascii"),
                }
            ),
        },
    )
    print(f"Created schedule: {schedule['ScheduleArn']}")


if __name__ == "__main__":
    main()
