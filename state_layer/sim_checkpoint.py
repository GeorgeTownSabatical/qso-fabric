from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SimulationCheckpoint:
    def __init__(self, state: Any) -> None:
        self.state = state
        self.timestamp: str | None = None

    def save_checkpoint(self) -> None:
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def load_checkpoint(self) -> Any:
        return self.state
