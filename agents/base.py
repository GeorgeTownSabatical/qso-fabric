from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentResult:
    status: str
    payload: dict[str, object]


@dataclass
class Agent:
    name: str

    def run(self, input_data: dict[str, object]) -> AgentResult:
        raise NotImplementedError
