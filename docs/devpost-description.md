# Devpost text description (under 300 words)

Guardrail watches an elderly parent's bank account on behalf of her family,
not her bank.

Adults over 60 reported about $4.8 billion in fraud losses to the FBI in 2024
[verify against the IC3 report before submitting], and the common scams share
a shape: a burst of gift cards after an "emergency" call, one large wire to a
new payee, a remote-access purchase followed by an ATM run. Banks optimize
alerts for their own losses; the daughter 2,000 miles away finds out after
the money is gone.

Guardrail is a three-agent Strands pipeline on Amazon Bedrock AgentCore
Runtime, invoked every morning by EventBridge Scheduler. The Monitor agent
scores transactions against a behavioral baseline with deterministic tools;
the model never does the math. The Verifier agent corroborates from features
the Monitor never examined: round amounts, tight time windows, unfamiliar
merchant categories. A flag without independent evidence stays silent. The
Escalation agent drafts a plain-language message and requests approval; it
cannot send, and a Strands steering guard pins the approval's recipient to
the pipeline's own values, so a hallucinated actor ID becomes a correction
instead of a misdirected link. If an agent fails outright, the pipeline
fails open toward a human. Every tool call is recorded by hooks and shown as
an audit trail, so each alert explains why it fired. When the family
dismisses an alert, those merchants join the elder's baseline, and the same
pattern is quiet tomorrow.

Most days Guardrail does nothing, and the trend page shows that silence is
the system working.

Track: Everyday Agents. Audience: adult children of aging parents. Honest
limits: Plaid-shaped synthetic data, one demo PIN, link shown instead of
SMS. Each is a documented swap, not a rewrite.
