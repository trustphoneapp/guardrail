# Building Guardrail for Agents for Humans: what the docs didn't tell me about Strands and AgentCore

*Draft for builder.aws.com. The title contains "Agents for Humans" as the
bonus rules require. Tutorial-shaped: the five things I had to discover the
hard way, so you don't.*

My mother is not Sarla, but everyone knows a Sarla: 78, lives alone, answers
the phone. For the Agents for Humans hackathon I built Guardrail, a
three-agent Strands pipeline on Amazon Bedrock AgentCore that watches an
elder's transactions for scam signatures and asks her daughter before anyone
acts. This post is not the pitch; it is the build log. Five findings, each
one verified in code you can run.

## 1. The deprecated structured-output path can skip your tools entirely

`agent.structured_output(Model, prompt=...)` is deprecated, and on some runs
it skipped the tool-calling loop and returned a guess with zero grounding in
what my deterministic scoring tool computed. The supported form,
`agent(prompt, structured_output_model=Model)`, ran the full tool loop every
time. If your architecture's honesty depends on "the model reports exactly
what the tool said," verify it by reading `agent.messages`, not the docstring.

## 2. Put real JSON in prompts, not Python reprs

I embedded a list of pydantic dumps in an f-string. Locally, fine. In
production, Nova Pro occasionally echoed that single-quoted repr syntax back
into a tool call's arguments, and Bedrock rejected the request:
"toolUse.input is invalid. Provide a json object." `json.dumps()` in the
prompt ended it. The bug only appeared under the deployed runtime's load,
and only sometimes, which is exactly the kind of bug you want to have read
about in someone else's blog post.

## 3. EventBridge Scheduler's universal target name is not the service name

To invoke an AgentCore runtime on a schedule, the universal target ARN is
`arn:aws:scheduler:::aws-sdk:bedrockagentcore:invokeAgentRuntime`. Not
`bedrock-agentcore`, which fails with "api not valid for the service." The
identifier is the SDK serviceId ("Bedrock AgentCore") lowercased with spaces
removed. I found it by introspecting botocore's service model, which is
faster than guessing hyphenation.

## 4. Lambda Function URLs need a second permission since October 2025

My public dashboard returned 403 with a correct-looking resource policy.
New function URLs now require `lambda:InvokeFunction` with the
`lambda:InvokedViaFunctionUrl` condition in addition to
`lambda:InvokeFunctionUrl`. Also: Lambda rejects buildx's default OCI
manifests; build with `--provenance=false` and `oci-mediatypes=false`.

## 5. An env-var update is not necessarily the env your container sees

After updating my AgentCore runtime's environment variables, the config
showed them and my invocations did not have them: instances provisioned
moments before the update kept serving. I added a debug flag to the payload
that reports the env the container actually sees. When state silently falls
back to an in-process dict, you want that flag to exist.

## The part I would defend in a design review

Strands' Graph is the right topology for this pipeline and it is not what
runs. Graph forwards each node's free-text output; I needed typed JSON on
every edge and gates testable without a model call. So the nodes are
unchanged Strands Agents and the edges are forty lines of Python with
pydantic contracts. The supervision is Strands all the way down though: a
hooks-based audit trail records every tool call, and the vended steering
plugin pins the approval tool's recipient to the pipeline's computed values,
so a hallucinated actor ID becomes a correction, not a misdirected link.

Repo, live dashboard, and the demo video are linked from the Devpost
submission. Everything in this post has a test or a CloudWatch log behind it.
