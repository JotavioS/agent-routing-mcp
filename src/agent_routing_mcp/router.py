from __future__ import annotations

from typing import Any

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

DIFFICULTY_QUESTION = {
    "type": "score",
    "instructions": "How hard is the request for a language model?",
    "criteria": [
        "trivial: a lookup or one-liner",
        "easy: short answer, no reasoning",
        "moderate: several steps",
        "hard: long multi-step reasoning or specialist knowledge",
    ],
}

UPPER_ROUTE_QUESTION = {
    "type": "choice",
    "instructions": (
        "Choose the lowest sufficient upper execution lane for this "
        "software-engineering task."
    ),
    "criteria": {
        Route.HIGH.value: (
            "Complex multi-file implementation or debugging requiring substantial "
            "cross-module reasoning, but the overall architecture is known and "
            "lower-capability attempts have not repeatedly failed."
        ),
        Route.ESCALATE.value: (
            "System-level architecture redesign, security-critical design, highly "
            "ambiguous cross-system work, no-downtime architectural migration, or "
            "work that has already repeatedly failed on lower-capability attempts."
        ),
    },
}


class ModelRouter:
    def __init__(
        self,
        *,
        provider: DecisionProvider,
        routes: dict[Route, RouteTarget],
        ambiguity_margin: float = 0.10,
        strategy: str = "choice",
        low_score_max: float = 1.45,
        medium_score_max: float = 2.10,
    ) -> None:
        self.provider = provider
        self.routes = routes
        self.ambiguity_margin = ambiguity_margin
        self.strategy = strategy
        self.low_score_max = low_score_max
        self.medium_score_max = medium_score_max

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

        if self.strategy == "hierarchical":
            result = self._route_hierarchical(state)
        else:
            result = self._route_choice(state)

        route = result.route

        if security_sensitive and route in {Route.LOW, Route.MEDIUM}:
            route = Route.HIGH

        if previous_attempts >= 2 or failed_checks >= 2:
            if route in {Route.LOW, Route.MEDIUM}:
                route = Route.HIGH

        if route == result.route:
            return result

        target = self.routes[route]
        details = dict(result.details or {})
        details["policy_floor"] = route.value

        return RoutingResult(
            route=route,
            model=target.model,
            reasoning_effort=target.reasoning_effort,
            confidence=result.confidence,
            margin=result.margin,
            ambiguous=result.ambiguous,
            probabilities=result.probabilities,
            details=details,
        )

    def _route_choice(self, state: str) -> RoutingResult:
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

        target = self.routes[decision.choice]

        return RoutingResult(
            route=decision.choice,
            model=target.model,
            reasoning_effort=target.reasoning_effort,
            confidence=top_probability,
            margin=margin,
            ambiguous=margin < self.ambiguity_margin,
            probabilities={
                key.value: value
                for key, value in decision.probabilities.items()
            },
            details={"strategy": "choice"},
        )

    def _route_hierarchical(self, state: str) -> RoutingResult:
        body = self.provider.system_one(
            state={"request": state},
            questions={
                "difficulty": DIFFICULTY_QUESTION,
                "upper_route": UPPER_ROUTE_QUESTION,
            },
        )
        answers = body["answers"]
        difficulty = answers["difficulty"]
        upper = answers["upper_route"]

        score = float(difficulty["score"])
        difficulty_probabilities = {
            str(key): float(value)
            for key, value in difficulty["probabilities"].items()
        }
        upper_probabilities = {
            Route(key): float(value)
            for key, value in upper["probabilities"].items()
        }

        if score < self.low_score_max:
            route = Route.LOW
        elif score < self.medium_score_max:
            route = Route.MEDIUM
        else:
            route = Route(upper["choice"])

        # Convert the two-stage decision into a normalized support distribution.
        # Difficulty levels 0/1 represent low-complexity work, level 2 routine
        # multi-step work, and level 3 is split by the upper-lane decision.
        easy_mass = (
            difficulty_probabilities.get("0", 0.0)
            + difficulty_probabilities.get("1", 0.0)
        )
        moderate_mass = difficulty_probabilities.get("2", 0.0)
        hard_mass = difficulty_probabilities.get("3", 0.0)

        probabilities = {
            Route.LOW.value: easy_mass,
            Route.MEDIUM.value: moderate_mass,
            Route.HIGH.value: hard_mass * upper_probabilities.get(Route.HIGH, 0.0),
            Route.ESCALATE.value: (
                hard_mass * upper_probabilities.get(Route.ESCALATE, 0.0)
            ),
        }
        total = sum(probabilities.values())
        if total > 0:
            probabilities = {
                key: value / total
                for key, value in probabilities.items()
            }

        chosen_support = probabilities.get(route.value, 0.0)
        strongest_other = max(
            (value for key, value in probabilities.items() if key != route.value),
            default=0.0,
        )
        support_margin = chosen_support - strongest_other

        if route in {Route.HIGH, Route.ESCALATE}:
            upper_other = (
                Route.ESCALATE if route == Route.HIGH else Route.HIGH
            )
            stage_margin = (
                upper_probabilities.get(route, 0.0)
                - upper_probabilities.get(upper_other, 0.0)
            )
            confidence = upper_probabilities.get(route, 0.0)
        else:
            stage_margin = support_margin
            confidence = chosen_support

        boundary_distance = min(
            abs(score - self.low_score_max),
            abs(score - self.medium_score_max),
        )
        ambiguous = (
            stage_margin < self.ambiguity_margin
            or boundary_distance < self.ambiguity_margin
        )

        target = self.routes[route]
        return RoutingResult(
            route=route,
            model=target.model,
            reasoning_effort=target.reasoning_effort,
            confidence=confidence,
            margin=stage_margin,
            ambiguous=ambiguous,
            probabilities=probabilities,
            details={
                "strategy": "hierarchical",
                "difficulty_score": score,
                "difficulty_probabilities": difficulty_probabilities,
                "upper_choice": upper["choice"],
                "upper_probabilities": {
                    key.value: value
                    for key, value in upper_probabilities.items()
                },
                "low_score_max": self.low_score_max,
                "medium_score_max": self.medium_score_max,
            },
        )
