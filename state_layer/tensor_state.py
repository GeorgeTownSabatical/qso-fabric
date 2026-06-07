from __future__ import annotations

from typing import Any, List


class TensorState:
    def __init__(self, shape: List[int], dtype: str = "complex64") -> None:
        self.shape = shape
        self.dtype = dtype
        self.tensor: Any = None

    def update(self, patch: Any) -> None:
        self.tensor = patch

    def read(self) -> Any:
        return self.tensor
