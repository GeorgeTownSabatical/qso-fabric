from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QSOURI:
    raw: str

    def __post_init__(self) -> None:
        if not self.raw.startswith("qso://"):
            raise ValueError(f"invalid qso uri: {self.raw}")
        if len(self.raw) <= 6:
            raise ValueError("qso uri must include a namespace")

    @property
    def namespace(self) -> str:
        body = self.raw[len("qso://") :]
        return body.split(".", 1)[0]


def is_qso_uri(value: str) -> bool:
    try:
        QSOURI(value)
    except ValueError:
        return False
    return True
