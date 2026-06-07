from __future__ import annotations

from abc import ABC, abstractmethod

from services.quantum.models import QuantumExecutionResult, QuantumJob


class QuantumBackend(ABC):
    name: str

    @abstractmethod
    def execute(self, job: QuantumJob) -> QuantumExecutionResult:
        raise NotImplementedError
