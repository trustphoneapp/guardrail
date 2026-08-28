# Demo video script — from the 0:32 intro handoff (target 4:10, cap 5:00)

Segment 1 (0:00–0:32) is the finished HeyGen storybook intro and is locked.
It ends on: "This is Guardrail... Here's the real thing." Everything below is
the screencast that starts on that cut.

Ground rules for recording: everything runs against the live deployed stack,
nothing mocked. Terminal at 18pt+ font, dark theme, browser at 125% zoom.
Corner badge "Strands | AgentCore | Nova Pro" on screen from 0:32 to the end.
Narrate under 140 words per minute — slower than feels natural.

Pre-flight (do all of this BEFORE recording anything):
- [ ] Verify the FBI IC3 elder-fraud dollar figure against the 2024 report PDF; the
      narration below says "almost five billion dollars" — correct it if wrong.
- [ ] `curl <dashboard>/health` returns ok; runtime READY; open tabs: trend page,
      GitHub repo (Actions tab showing green), README.
- [ ] One fresh terminal, `cd ~/Projects/guardrail`, profile env ready.
- [ ] Do one throwaway invoke first so the runtime is warm (avoids a 15s cold
      stall on camera).

---

## 0:32–1:10 — The scam, caught live (the aha, immediately)

SCREEN: terminal. Run:

    AWS_PROFILE=guardrail python scripts/run_local.py --scenario grandparent_scam

While it runs, NARRATE:

> "Scammers took almost five billion dollars from older Americans last year,
> and most families found out after the money was gone. So here is that story
> again — for real. Three five-hundred-dollar gift cards, bought in one
> afternoon, on a live AWS deployment."

When the escalated result prints, point at it (cursor highlight) and read:

> "The Monitor flagged it: three gift-card purchases in one window. The
> Verifier double-checked with evidence the Monitor never looked at — round
> amounts, a tight time window — and agreed. And the Escalation agent drafted
> a message and minted a signed approval link. Nobody's been called yet.
> Nothing's been touched."

## 1:10–1:45 — Priya's phone

SCREEN: browser, the printed approval link on the public dashboard.

1. Open the link — the redacted stub page. NARRATE:
> "Priya gets this link. Before her PIN, it shows nothing — no amounts, no
> merchants, in case the link leaks."
2. Type a WRONG pin first. Show the "4 attempts remaining" error:
> "Wrong PIN counts down. Five misses burn the link forever."
3. Right PIN → evidence trail renders:
> "The right PIN shows her exactly why: which purchases, which pattern, how
> confident. And these two buttons are the only actions that exist —
> Guardrail can never freeze a card or move a dollar. It can only tap a
> human on the shoulder."
4. Paste the same link again → "token already used":
> "Used once, dead forever."

## 1:45–2:15 — The boring page that means everything is fine

SCREEN: the public trend page for sarla-demo-001.

> "This is my favorite screen, and it's the most boring one. Every row is a
> morning Guardrail checked her account. See these quiet-day rows? No human
> triggered them — an EventBridge schedule has been waking this agent every
> day for a week while we did nothing. Silence here isn't the system idle.
> Silence is the product."

Expand one row's audit trail:

> "And every run keeps its receipts: which agent called which tool, in what
> order, how long it took."

## 2:15–2:40 — The family teaches it

SCREEN: back on the evidence page. Click "This was Mom, dismiss." Then re-run
the same scenario in the terminal; it comes back quiet.

> "One more thing. When Priya says 'that was actually Mom' — Guardrail
> learns. Same purchases, next morning: quiet. The family's judgment becomes
> the baseline."

## 2:40–3:10 — Why you can trust it (constitution + architecture)

SCREEN: CONSTITUTION.md on GitHub, scroll slowly. Then the README diagram.

> "The architecture is three Strands agents on Amazon Bedrock AgentCore, and
> one short file governs them: the constitution. The model never does the
> math — every flag is a deterministic rule you can unit-test. The model
> never sends — token minting is plain Python it can't reach. A steering
> guard means it can't even route an alert to the wrong family. And if an
> agent crashes outright, the pipeline fails open — it wakes a human rather
> than going quiet. Every rule names the code and the test that enforce it."

## 3:10–3:40 — Prove it yourself in one command

SCREEN: terminal. Run:

    python scripts/sweep.py

> "You don't have to trust the video. One command runs every scenario
> through the real detection core — no credentials, no model, one second.
> Quiet days stay quiet, four scam shapes wake a human. Forty-seven tests
> and a full-history secret scan run green in CI on every push."

Cut briefly to the GitHub Actions green checks.

## 3:40–4:00 — Honest limits

SCREEN: one plain slide, three lines:
  - Transaction stream: Plaid-shaped synthetic data, labeled as such
  - Alerts: link shown on screen instead of a real SMS
  - One demo PIN instead of per-family enrollment

> "What's not real yet, on purpose: the bank feed is sandboxed synthetic
> data, the text message is a link on screen, and there's one demo PIN. Each
> one is a documented swap — production Plaid, SNS, per-family enrollment —
> not a rewrite."

## 4:00–4:10 — End card

SCREEN: title card — Guardrail. Repo URL, live dashboard URL, "Agents for
Humans" hackathon, Everyday Agents track.

> "Guardrail. It watches quietly, so someone you love doesn't lose
> everything loudly."

---

## Assembly notes

- Export the HeyGen intro at 1080p, stitch in iMovie/CapCut: intro (0:32) +
  screencast. Hard cut on "Here's the real thing," no transition effect.
- Total runtime lands ~4:10 against the 5:00 cap — do not fill the slack.
- Upload to YouTube (public or unlisted-with-link per Devpost rules).
- After upload: click every link in the description from an incognito window.
