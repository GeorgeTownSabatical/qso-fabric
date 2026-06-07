from __future__ import annotations

from .base import Agent, AgentResult


class Theorist(Agent):
    def run(self, input_data: dict[str, object]) -> AgentResult:
        return AgentResult(status="ok", payload={"hypotheses": [], "input": input_data})
