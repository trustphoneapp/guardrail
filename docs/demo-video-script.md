# Demo video script (target 4:20, cap 5:00)

Record all footage against the live deployed stack. Everything in this script
ran live on Aug 22; nothing is a mockup. Corner badge "Strands | AgentCore |
Nova Pro" stays on the whole video. Narrate under 140 words per minute.

## 0:00-0:15 — Hook (verbatim, over a title card)

"Last year Americans over sixty reported four point eight billion dollars
stolen by scammers, and most families found out after the money was gone.
This is Guardrail: three Strands agents on Amazon Bedrock AgentCore that
check an elderly parent's account every morning, stay silent when nothing is
wrong, and when something looks like a scam, ask her daughter before anyone
acts. Here it is running live."

[Verify the $4.8B figure against the FBI IC3 2024 elder fraud report PDF
before recording. If it differs, use the real number.]

## 0:15-0:40 — The people and the problem

Sarla, 78. Priya, 2,000 miles away. Banks flag fraud for the bank's losses;
nobody watches for the family. One slide, three scam shapes: gift-card burst
after an "emergency" call, one large wire to a stranger, remote-access
purchase then an ATM run.

## 0:40-1:05 — Architecture (one diagram, one sentence of trust)

The README mermaid diagram: Scheduler, AgentCore Runtime, Monitor, Verifier,
Escalation, DynamoDB, dashboard. Sandbox components visibly labeled.
Say: "The model never does the math, and it can never send. Watch the
Verifier: it corroborates from features the Monitor never saw."

## 1:05-1:35 — Quiet day, live

Invoke the deployed runtime with scenario quiet_day (real ~8s run;
jump-cut with an on-screen "trimmed, real run"). Show the response: status
quiet. Open the public trend page: the quiet row, its audit trail expanded,
four tool calls. Say: "Silence is the product. Most days this is the whole
story."

## 1:35-2:30 — Grandparent scam, live

Invoke with grandparent_scam. Show the response fields as callouts:
Monitor's deterministic reason ("3 gift-card purchases in one window"),
Verifier's independent_features (round_amounts), the scam_pattern name.
Show the trend page audit trail: monitor's three tools, verifier's
cross-check, escalation's draft + request. Say: "If either agent crashes,
the pipeline fails open toward Priya, and there's a test that proves it."

## 2:30-3:15 — Priya's side, on the public URL

The redacted page (no name, no amounts). PIN. The evidence trail: three $500
gift cards, the pattern, the confidence. Paste the link again: "token
already used." Say: "Signed, single-use, fifteen minutes, five wrong PINs
burns it. This page is the only action Guardrail takes: nothing is frozen,
nothing is moved."

## 3:15-3:40 — Close the loop, live

Click "This was Mom, dismiss." Show the merchants entering the baseline.
Re-invoke the same scenario: quiet. Say: "The family's answer isn't a log
line. It's what the system knows tomorrow."

## 3:40-4:05 — Honest slide

Two columns. Real and verified: the three agents, AgentCore deployment,
daily schedule, tokens, audit trail, fail-open. Sandboxed: Plaid-shaped
synthetic stream, one demo PIN, link shown instead of SMS. Say: "Each of
these is a swap, not a rewrite, and none is hidden."

## 4:05-4:20 — End card

Repo URL, live dashboard URL, builder.aws post title. "Built solo on
Strands and AgentCore for Agents for Humans."
