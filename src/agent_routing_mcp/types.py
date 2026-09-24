from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Route(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class Decision:
    choice: Route
    confidence: float
    probabilities: dict[Route, float]


@dataclass(frozen=True)
class RouteTarget:
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class RoutingResult:
    route: Route
    model: str
    reasoning_effort: str
    confidence: float
    margin: float
    ambiguous: bool
    probabilities: dict[str, float]
    details: dict[str, Any] | None = None
