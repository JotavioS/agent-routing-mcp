from __future__ import annotations

import json
import urllib.request
from typing import Any

from agent_routing_mcp.types import Decision, Route


class SystemOneHTTPProvider:
    """HTTP adapter for typed-decision services exposing /v1/systemone semantics."""

    def __init__(self, url: str, timeout_seconds: float = 5.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "state": state,
            "questions": questions,
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)

    def choose(
        self,
        *,
        state: str,
        question: str,
        choices: dict[str, str],
    ) -> Decision:
        body = self.system_one(
            state=state,
            questions={
                "route": {
                    "type": "choice",
                    "instructions": question,
                    "criteria": choices,
                }
            },
        )

        answer = body["answers"]["route"]
        probabilities = {
            Route(key): float(value)
            for key, value in answer["probabilities"].items()
        }

        choice = Route(answer["choice"])
        return Decision(
            choice=choice,
            confidence=float(answer.get("answer_confidence", probabilities[choice])),
            probabilities=probabilities,
        )
