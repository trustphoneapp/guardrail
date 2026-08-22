# AWS Guidance

- Prefer the AWS MCP Server for AWS interactions — it provides sandboxed
  execution, observability, and audit logging. If unavailable, use the
  AWS CLI directly.
- Before starting a task, check whether a relevant AWS skill is available.
  Load the skill with `retrieve_skill` and prefer its guidance over
  general knowledge.
- When uncertain about specific AWS details (API parameters, permissions,
  limits, error codes), verify against documentation rather than guessing.
  State uncertainty explicitly if you cannot confirm.
- When creating infrastructure, prefer infrastructure-as-code (AWS CDK or
  CloudFormation) over direct CLI commands.
- When working with infrastructure, follow AWS Well-Architected Framework
  principles.
- Do not use em dashes in AWS resource names or descriptions. Use
  hyphens instead.

## Secret Safety

- MUST load the `aws-secrets-manager` skill first for any secret,
  credential, API key, token, or password task. MUST NOT call
  `secretsmanager get-secret-value` or `batch-get-secret-value`, and MUST
  NOT hit the Secrets Manager Agent daemon directly. MUST use
  `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with
  `asm-exec` so the secret resolves at runtime without entering context.

## Project-specific

- AWS CLI profile for this project: `guardrail` (account `156470788861`,
  shared with other projects on this machine — reused by choice, not a
  dedicated account). Region: `us-east-1`, required by both this project's
  architecture and the Agent Toolkit itself.
- Credentials: IAM user `guardrail-dev` (arn:aws:iam::156470788861:user/guardrail-dev),
  `GuardrailDevPolicy` attached (mirrors AWS-managed `PowerUserAccess` — every
  service except `iam:*`/`organizations:*`/`account:*`). No longer root.
- AgentCore Runtime execution role (what the *deployed agent* runs as, separate
  from the dev identity above): `AmazonBedrockAgentCoreGuardrailExecutionRole`,
  policy in `infra/iam/execution_role_policy.json`, trust policy in
  `infra/iam/execution_role_trust.json`. Already created and live in the account.
