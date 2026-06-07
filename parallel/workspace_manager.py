from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workspace:
    name: str
    path: str


def create_workspace(name: str, path: str) -> Workspace:
    return Workspace(name=name, path=path)
