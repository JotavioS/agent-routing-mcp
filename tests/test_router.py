from agent_routing_mcp.router import ModelRouter
from agent_routing_mcp.types import Decision, Route, RouteTarget


class StubProvider:
    def __init__(self, decision: Decision) -> None:
        self.decision = decision

    def choose(self, **kwargs):
        return self.decision


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
