from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from agent_routing_mcp.types import Route, RouteTarget


@dataclass(frozen=True)
class ProviderConfig:
    type: str
    url: str
    timeout_seconds: float


@dataclass(frozen=True)
class AppConfig:
    provider: ProviderConfig
    ambiguity_margin: float
    routes: dict[Route, RouteTarget]


def load_config() -> AppConfig:
    path = Path(os.environ.get("AGENT_ROUTING_CONFIG", "routing.json"))
    raw = json.loads(path.read_text(encoding="utf-8"))

    provider_raw = raw["decision_provider"]
    provider = ProviderConfig(
        type=provider_raw["type"],
        url=provider_raw["url"],
        timeout_seconds=float(provider_raw.get("timeout_seconds", 5)),
    )

    routes = {
        Route(name): RouteTarget(
            model=data["model"],
            reasoning_effort=data["reasoning_effort"],
        )
        for name, data in raw["routes"].items()
    }

    missing = set(Route) - set(routes)
    if missing:
        raise ValueError(f"missing route mappings: {sorted(item.value for item in missing)}")

    return AppConfig(
        provider=provider,
        ambiguity_margin=float(raw.get("ambiguity_margin", 0.10)),
        routes=routes,
    )
