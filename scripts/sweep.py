"""The judge's one command: run every scenario through the deterministic core
and print the verdict table. Zero credentials, zero model calls, ~1 second.

    python scripts/sweep.py

This is the same detection and corroboration code the deployed agents call as
tools; the only thing skipped is the LLM orchestration around it (see
CONSTITUTION.md rule 3 -- the model never does the math, so the math is fully
demonstrable without the model). Exits nonzero if any scenario lands on the
wrong side, so it doubles as a regression gate.
"""

import sys

from guardrail.synthetic.baseline_generator import generate_baseline
from guardrail.synthetic.scenarios import SCENARIOS
from guardrail.tools.baseline_tools import score_deviation
from guardrail.tools.corroboration_tools import cross_check_signals

EXPECT_QUIET = {"quiet_day", "quiet_day_second_elder"}


def main() -> int:
    baseline = generate_baseline("sweep-demo").model_dump(mode="json")
    rows, failures = [], 0

    for name, scenario in SCENARIOS.items():
        txns = [t.model_dump(mode="json") for t in scenario["transactions"]]
        monitor = score_deviation(transactions=txns, baseline=baseline)
        if monitor["flagged"]:
            verifier = cross_check_signals(signals=monitor["signals"], transactions=txns, baseline=baseline)
            verdict = "ESCALATE" if verifier["corroborated"] else "quiet (unverified)"
            detail = verifier["scam_pattern"] or "-"
        else:
            verdict = "quiet"
            detail = "-"

        expected_quiet = name in EXPECT_QUIET
        ok = (verdict == "quiet") == expected_quiet
        failures += 0 if ok else 1
        rows.append((name, verdict, detail, "ok" if ok else "WRONG"))

    w = max(len(r[0]) for r in rows) + 2
    print(f"{'scenario':<{w}}{'verdict':<20}{'pattern':<28}check")
    print("-" * (w + 54))
    for name, verdict, detail, ok in rows:
        print(f"{name:<{w}}{verdict:<20}{detail:<28}{ok}")

    print()
    if failures:
        print(f"{failures} scenario(s) landed on the wrong side.")
        return 1
    print(f"All {len(rows)} scenarios landed where they should. Quiet days stay quiet; scams wake a human.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
