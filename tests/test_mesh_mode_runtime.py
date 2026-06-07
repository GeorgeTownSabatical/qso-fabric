from __future__ import annotations

from pathlib import Path

import pytest

from services.runtime import QSOFabricRuntime
from storage.checkpoint_store import JsonCheckpointStore
from storage.event_store import JsonlEventStore
from storage.snapshot_store import FileSnapshotStore


def _clear_mesh_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "QSO_MESH_MODE",
        "QSO_EVENT_STORE_PATH",
        "QSO_CHECKPOINT_STORE_PATH",
        "QSO_SNAPSHOT_STORE_DIR",
        "QSO_NETWORK_AUDIT_PATH",
        "QSO_TRANSPORT_STATE_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_mesh_mode_fails_closed_when_required_paths_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_mesh_env(monkeypatch)
    monkeypatch.setenv("QSO_MESH_MODE", "1")

    with pytest.raises(RuntimeError, match="mesh_mode_requires_env"):
        QSOFabricRuntime()


def test_mesh_mode_allows_start_with_persistent_stores(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_mesh_env(monkeypatch)
    monkeypatch.setenv("QSO_MESH_MODE", "1")
    monkeypatch.setenv("QSO_EVENT_STORE_PATH", str(tmp_path / "events" / "events.jsonl"))
    monkeypatch.setenv("QSO_CHECKPOINT_STORE_PATH", str(tmp_path / "checkpoints" / "checkpoints.json"))
    monkeypatch.setenv("QSO_SNAPSHOT_STORE_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("QSO_NETWORK_AUDIT_PATH", str(tmp_path / "audit" / "network_audit.jsonl"))
    monkeypatch.setenv("QSO_TRANSPORT_STATE_PATH", str(tmp_path / "transport" / "transport_state.json"))

    runtime = QSOFabricRuntime()

    assert runtime.mesh_mode is True
    assert isinstance(runtime.event_store, JsonlEventStore)
    assert isinstance(runtime.checkpoint_store, JsonCheckpointStore)
    assert isinstance(runtime.snapshot_store, FileSnapshotStore)
