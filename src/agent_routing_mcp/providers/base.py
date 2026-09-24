from __future__ import annotations

from typing import Any, Protocol

from agent_routing_mcp.types import Decision


class DecisionProvider(Protocol):
    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate bounded typed questions and return their answers."""
        ...

    def choose(
        self,
        *,
        state: str,
        question: str,
        choices: dict[str, str],
    ) -> Decision:
        """Choose exactly one bounded option from the supplied choices."""
        ...
