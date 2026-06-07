from __future__ import annotations

from typing import Any, List


class WaveState:
    def __init__(self, shape: List[int]) -> None:
        self.shape = shape
        self.wave: Any = None

    def update_phase(self, phase_patch: Any) -> None:
        self.wave = phase_patch

    def read_wave(self) -> Any:
        return self.wave
