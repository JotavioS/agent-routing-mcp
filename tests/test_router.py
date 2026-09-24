from agent_routing_mcp.router import ModelRouter
from agent_routing_mcp.types import Decision, Route, RouteTarget


class StubProvider:
    def __init__(self, decision: Decision) -> None:
        self.decision = decision

    def choose(self, **kwargs):
        return self.decision


class HierarchicalStubProvider:
    def __init__(
        self,
        *,
        score: float,
        difficulty_probabilities: dict[str, float],
        upper_choice: str,
        upper_probabilities: dict[str, float],
    ) -> None:
        self.score = score
        self.difficulty_probabilities = difficulty_probabilities
        self.upper_choice = upper_choice
        self.upper_probabilities = upper_probabilities

    def system_one(self, **kwargs):
        return {
            "answers": {
                "difficulty": {
                    "type": "score",
                    "score": self.score,
                    "probabilities": self.difficulty_probabilities,
                },
                "upper_route": {
                    "type": "choice",
                    "choice": self.upper_choice,
                    "probabilities": self.upper_probabilities,
                },
            }
        }


ROUTES = {
    Route.LOW: RouteTarget("cheap", "low"),
    Route.MEDIUM: RouteTarget("cheap", "medium"),
    Route.HIGH: RouteTarget("cheap", "high"),
    Route.ESCALATE: RouteTarget("strong", "high"),
}


def make_router(choice: Route, probabilities: dict[Route, float]) -> ModelRouter:
    return ModelRouter(
        provider=StubProvider(
            Decision(
                choice=choice,
                confidence=probabilities[choice],
                probabilities=probabilities,
            )
        ),
        routes=ROUTES,
        ambiguity_margin=0.10,
    )


def test_routes_selected_lane_to_configured_model():
    router = make_router(
        Route.MEDIUM,
        {
            Route.LOW: 0.10,
            Route.MEDIUM: 0.60,
            Route.HIGH: 0.20,
            Route.ESCALATE: 0.10,
        },
    )

    result = router.route(task="Implement a routine endpoint")

    assert result.route == Route.MEDIUM
    assert result.model == "cheap"
    assert result.reasoning_effort == "medium"
    assert result.ambiguous is False


def test_reports_close_decision_as_ambiguous():
    router = make_router(
        Route.MEDIUM,
        {
            Route.LOW: 0.10,
            Route.MEDIUM: 0.36,
            Route.HIGH: 0.35,
            Route.ESCALATE: 0.19,
        },
    )

    result = router.route(task="Complex task")

    assert result.ambiguous is True
    assert round(result.margin, 2) == 0.01


def test_security_sensitive_work_has_high_floor():
    router = make_router(
        Route.LOW,
        {
            Route.LOW: 0.70,
            Route.MEDIUM: 0.20,
            Route.HIGH: 0.05,
            Route.ESCALATE: 0.05,
        },
    )

    result = router.route(
        task="Change authentication behavior",
        security_sensitive=True,
    )

    assert result.route == Route.HIGH
    assert result.reasoning_effort == "high"


def test_repeated_failures_have_high_floor():
    router = make_router(
        Route.MEDIUM,
        {
            Route.LOW: 0.10,
            Route.MEDIUM: 0.70,
            Route.HIGH: 0.10,
            Route.ESCALATE: 0.10,
        },
    )

    result = router.route(
        task="Fix persistent test failure",
        failed_checks=2,
    )

    assert result.route == Route.HIGH


def test_hierarchical_strategy_uses_score_for_low_and_medium():
    low_router = ModelRouter(
        provider=HierarchicalStubProvider(
            score=1.10,
            difficulty_probabilities={"0": 0.20, "1": 0.60, "2": 0.15, "3": 0.05},
            upper_choice="HIGH",
            upper_probabilities={"HIGH": 0.70, "ESCALATE": 0.30},
        ),
        routes=ROUTES,
        strategy="hierarchical",
    )
    medium_router = ModelRouter(
        provider=HierarchicalStubProvider(
            score=1.80,
            difficulty_probabilities={"0": 0.05, "1": 0.20, "2": 0.60, "3": 0.15},
            upper_choice="HIGH",
            upper_probabilities={"HIGH": 0.70, "ESCALATE": 0.30},
        ),
        routes=ROUTES,
        strategy="hierarchical",
    )

    assert low_router.route(task="small edit").route == Route.LOW
    assert medium_router.route(task="routine feature").route == Route.MEDIUM


def test_hierarchical_strategy_splits_upper_lane():
    high_router = ModelRouter(
        provider=HierarchicalStubProvider(
            score=2.30,
            difficulty_probabilities={"0": 0.02, "1": 0.08, "2": 0.30, "3": 0.60},
            upper_choice="HIGH",
            upper_probabilities={"HIGH": 0.75, "ESCALATE": 0.25},
        ),
        routes=ROUTES,
        strategy="hierarchical",
    )
    escalate_router = ModelRouter(
        provider=HierarchicalStubProvider(
            score=2.30,
            difficulty_probabilities={"0": 0.02, "1": 0.08, "2": 0.30, "3": 0.60},
            upper_choice="ESCALATE",
            upper_probabilities={"HIGH": 0.25, "ESCALATE": 0.75},
        ),
        routes=ROUTES,
        strategy="hierarchical",
    )

    assert high_router.route(task="complex debugging").route == Route.HIGH
    assert escalate_router.route(task="architecture redesign").route == Route.ESCALATE
