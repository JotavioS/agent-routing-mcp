from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from mcp.server import MCPServer

from agent_routing_mcp.config import load_config
from agent_routing_mcp.providers.systemone_http import SystemOneHTTPProvider
from agent_routing_mcp.router import ModelRouter


mcp = MCPServer("agent-routing-mcp")


@lru_cache(maxsize=1)
def get_router() -> ModelRouter:
    config = load_config()

    if config.provider.type != "systemone_http":
        raise ValueError(
            f"unsupported decision provider type: {config.provider.type}"
        )

    provider = SystemOneHTTPProvider(
        url=config.provider.url,
        timeout_seconds=config.provider.timeout_seconds,
    )

    return ModelRouter(
        provider=provider,
        routes=config.routes,
        ambiguity_margin=config.ambiguity_margin,
        strategy=config.strategy.type,
        low_score_max=config.strategy.low_score_max,
        medium_score_max=config.strategy.medium_score_max,
    )


@mcp.tool()
def route_model(
    task: str,
    context: str = "",
    previous_attempts: int = 0,
    failed_checks: int = 0,
    security_sensitive: bool = False,
) -> dict:
    """Select the lowest sufficient configured execution model for a coding task.

    Use before delegating substantial software-engineering implementation.
    Do not use for deterministic verification such as tests, compilation,
    lint, type checking, git status, or git diff.
    """

    result = get_router().route(
        task=task,
        context=context,
        previous_attempts=previous_attempts,
        failed_checks=failed_checks,
        security_sensitive=security_sensitive,
    )

    return asdict(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
