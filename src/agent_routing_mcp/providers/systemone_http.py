from __future__ import annotations

import json
import urllib.request

from agent_routing_mcp.types import Decision, Route


class SystemOneHTTPProvider:
    """HTTP adapter for typed-decision services exposing /v1/systemone semantics."""

    def __init__(self, url: str, timeout_seconds: float = 5.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    def choose(
        self,
        *,
        state: str,
        question: str,
        choices: dict[str, str],
    ) -> Decision:
        payload = {
            "state": state,
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": question,
                    "criteria": choices,
                }
            },
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = json.load(response)

        answer = body["answers"]["route"]
        probabilities = {
            Route(key): float(value)
            for key, value in answer["probabilities"].items()
        }

        return Decision(
            choice=Route(answer["choice"]),
            confidence=float(answer.get("confidence", probabilities[Route(answer["choice"])])),
            probabilities=probabilities,
        )
