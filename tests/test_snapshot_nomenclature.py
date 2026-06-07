from __future__ import annotations

from core.naming.snapshot_terms import (
    SNAPSHOT_ENGINE_NAMESPACE,
    SNAPSHOT_PY_NAMESPACE,
    SNAPSHOTS_ARTIFACTS_DIRNAME,
    resolve_snapshot_artifact_path,
)
from tools.qso_nlm_ingest import _build_parser


def test_snapshot_nomenclature_contract_constants() -> None:
    assert SNAPSHOT_PY_NAMESPACE == "snapshot"
    assert SNAPSHOT_ENGINE_NAMESPACE == "snapshot_engine"
    assert SNAPSHOTS_ARTIFACTS_DIRNAME == "snapshots"


def test_snapshot_artifact_path_resolver_is_plural_rooted() -> None:
    assert str(resolve_snapshot_artifact_path("foo.qff")) == "snapshots/foo.qff"
    assert str(resolve_snapshot_artifact_path("snapshots/bar.qff")) == "snapshots/bar.qff"


def test_nlm_ingest_default_snapshot_path_uses_plural_artifact_root() -> None:
    parser = _build_parser()
    args = parser.parse_args([])
    assert str(args.snapshot_out).startswith("snapshots/")
