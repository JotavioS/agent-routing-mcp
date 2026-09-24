from __future__ import annotations

from agent_routing_mcp.providers.base import DecisionProvider
from agent_routing_mcp.types import Route, RouteTarget, RoutingResult


DEFAULT_CHOICES = {
    Route.LOW.value: (
        "One simple local edit; deterministic; no cross-file reasoning; "
        "no design decision."
    ),
    Route.MEDIUM.value: (
        "Routine implementation across a few files; standard validation "
        "and tests; limited ambiguity."
    ),
    Route.HIGH.value: (
        "Complex multi-file implementation or debugging; significant "
        "cross-module reasoning; substantial uncertainty."
    ),
    Route.ESCALATE.value: (
        "System architecture, security-critical design, unresolved ambiguity "
        "after investigation, or repeated failure of lower tiers."
    ),
}

DEFAULT_QUESTION = (
    "Classify the implementation difficulty. Select the least intensive "
    "category that is sufficient based only on scope, ambiguity, coupling, and risk."
)


class ModelRouter:
    def __init__(
        self,
        *,
        provider: DecisionProvider,
        routes: dict[Route, RouteTarget],
        ambiguity_margin: float = 0.10,
    ) -> None:
        self.provider = provider
        self.routes = routes
        self.ambiguity_margin = ambiguity_margin

    def route(
        self,
        *,
        task: str,
        context: str = "",
        previous_attempts: int = 0,
        failed_checks: int = 0,
        security_sensitive: bool = False,
    ) -> RoutingResult:
        state = task.strip()
        if context.strip():
            state += f"\n\nRelevant context:\n{context.strip()}"

        decision = self.provider.choose(
            state=state,
            question=DEFAULT_QUESTION,
            choices=DEFAULT_CHOICES,
        )

        ranked = sorted(
            decision.probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        top_probability = ranked[0][1]
        second_probability = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top_probability - second_probability

        route = decision.choice

        if security_sensitive and route in {Route.LOW, Route.MEDIUM}:
            route = Route.HIGH

        if previous_attempts >= 2 or failed_checks >= 2:
            if route in {Route.LOW, Route.MEDIUM}:
                route = Route.HIGH

        target = self.routes[route]

        return RoutingResult(
            route=route,
            model=target.model,
            reasoning_effort=target.reasoning_effort,
            confidence=top_probability,
            margin=margin,
            ambiguous=margin < self.ambiguity_margin,
            probabilities={
                key.value: value
                for key, value in decision.probabilities.items()
            },
        )
