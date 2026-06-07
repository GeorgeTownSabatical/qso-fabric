from __future__ import annotations

from .base import Agent, AgentResult


class Programmer(Agent):
    def run(self, input_data: dict[str, object]) -> AgentResult:
        return AgentResult(status="ok", payload={"artifacts": [], "input": input_data})
