from __future__ import annotations

from .base import Agent, AgentResult


class Experimentalist(Agent):
    def run(self, input_data: dict[str, object]) -> AgentResult:
        return AgentResult(status="ok", payload={"simulations": [], "input": input_data})
