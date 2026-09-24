from __future__ import annotations

from typing import Protocol

from agent_routing_mcp.types import Decision


class DecisionProvider(Protocol):
    def choose(
        self,
        *,
        state: str,
        question: str,
        choices: dict[str, str],
    ) -> Decision:
        """Choose exactly one bounded option from the supplied choices."""
        ...
