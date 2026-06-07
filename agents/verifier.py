from __future__ import annotations

from .base import Agent, AgentResult


class Verifier(Agent):
    def run(self, input_data: dict[str, object]) -> AgentResult:
        return AgentResult(status="ok", payload={"checks": [], "input": input_data})
