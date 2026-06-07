from __future__ import annotations

from .base import Agent, AgentResult


class Synthesizer(Agent):
    def run(self, input_data: dict[str, object]) -> AgentResult:
        return AgentResult(status="ok", payload={"summary": "", "input": input_data})
