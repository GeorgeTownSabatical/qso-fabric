from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import fcntl


@contextmanager
def exclusive_path_lock(path: str | Path) -> Iterator[None]:
    """Acquire a cross-process lock associated with a target filesystem path."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(f"{target.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: str | Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace a file with the provided text content."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name = f".{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    temp_path = target.with_name(temp_name)

    try:
        temp_path.write_text(text, encoding=encoding)
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
