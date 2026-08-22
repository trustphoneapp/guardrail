"""Per-run audit trail via Strands hooks.

One AuditTrail instance is created per pipeline run and passed to all three
agents. It subscribes to Before/AfterToolCallEvent and records every tool call
with its duration and a one-line result summary. run_pipeline attaches the
collected events to the run's trend row, and the dashboard renders them, which
turns "explain why this alert fired" from a sentence in the README into a
screen a judge can read.

The model is not involved in any of this; hooks fire in plain Python around
the tool calls the model makes.
"""

import time
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry


def _summarize(result: Any, limit: int = 160) -> str:
    text = str(result)
    return text if len(text) <= limit else text[: limit - 3] + "..."


class AuditTrail(HookProvider):
    def __init__(self) -> None:
        self.events: list[dict] = []
        self._started: dict[str, float] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self._before)
        registry.add_callback(AfterToolCallEvent, self._after)

    def _before(self, event: BeforeToolCallEvent) -> None:
        self._started[event.tool_use["toolUseId"]] = time.monotonic()

    def _after(self, event: AfterToolCallEvent) -> None:
        started = self._started.pop(event.tool_use["toolUseId"], None)
        self.events.append(
            {
                "agent": getattr(event.agent, "name", None) or "agent",
                "tool": event.tool_use["name"],
                "duration_ms": round((time.monotonic() - started) * 1000) if started else None,
                "ok": event.exception is None,
                "summary": _summarize(event.exception) if event.exception else _summarize(event.result.get("content")),
            }
        )
