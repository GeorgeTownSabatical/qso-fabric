from __future__ import annotations

from pathlib import Path

# Namespace terms are intentionally explicit to avoid singular/plural ambiguity.
SNAPSHOT_PY_NAMESPACE = "snapshot"
SNAPSHOT_ENGINE_NAMESPACE = "snapshot_engine"
SNAPSHOTS_ARTIFACTS_DIRNAME = "snapshots"


def default_snapshot_artifacts_dir() -> Path:
    """Canonical filesystem root for runtime-generated snapshot artifacts."""
    return Path(SNAPSHOTS_ARTIFACTS_DIRNAME)


def resolve_snapshot_artifact_path(relative_path: str | Path) -> Path:
    """
    Resolve snapshot artifact paths under the canonical artifact root.

    If an absolute path is provided, it is returned unchanged.
    """
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return candidate
    root = default_snapshot_artifacts_dir()
    text = candidate.as_posix()
    if text == SNAPSHOTS_ARTIFACTS_DIRNAME or text.startswith(f"{SNAPSHOTS_ARTIFACTS_DIRNAME}/"):
        return candidate
    return root / candidate
