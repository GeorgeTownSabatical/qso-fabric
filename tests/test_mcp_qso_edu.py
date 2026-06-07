from __future__ import annotations

from pathlib import Path

import pytest

from mcp_qso_edu.permissions import Capability, PermissionSet
from mcp_qso_edu.rate_limiter import RateLimitConfig
from mcp_qso_edu.server import QSOEduMCPServer


def test_sandbox_uri_rewrite_and_forbidden_root_isolation(tmp_path: Path) -> None:
    server = QSOEduMCPServer(state_root=tmp_path / "sandboxes")
    sandbox_id = server.create_sandbox("session-a")["sandbox_id"]

    created = server.qso_create(sandbox_id, "qso://infra.transport", {"type": "object"})
    payload = created["result"]

    assert payload["uri"].startswith(f"qso://sandbox/{sandbox_id}/")
    assert payload["forbidden_root_rewrite"] == "qso://infra.transport"


def test_sandbox_state_isolated_between_sessions(tmp_path: Path) -> None:
    server = QSOEduMCPServer(state_root=tmp_path / "sandboxes")
    sandbox_a = server.create_sandbox("token-a")["sandbox_id"]
    sandbox_b = server.create_sandbox("token-b")["sandbox_id"]

    server.qso_create(sandbox_a, "qso://demo/object", {"type": "object"})
    server.qso_patch(sandbox_a, "qso://demo/object", {"value": 5})

    with pytest.raises(KeyError):
        server.qso_read(sandbox_b, "qso://demo/object")


def test_permission_scoping_blocks_unauthorized_capabilities(tmp_path: Path) -> None:
    restricted = PermissionSet(capabilities={Capability.READ})
    server = QSOEduMCPServer(permissions=restricted, state_root=tmp_path / "sandboxes")
    sandbox_id = server.create_sandbox("restricted")["sandbox_id"]

    with pytest.raises(PermissionError):
        server.qso_create(sandbox_id, "qso://demo/object", {"type": "object"})


def test_rate_limiter_blocks_excessive_events(tmp_path: Path) -> None:
    server = QSOEduMCPServer(
        rate_limit_config=RateLimitConfig(max_events_per_minute=2, max_objects=10, max_entanglements=10),
        state_root=tmp_path / "sandboxes",
    )
    sandbox_id = server.create_sandbox("rate-limited")["sandbox_id"]

    server.qso_create(sandbox_id, "qso://demo/object", {"type": "object"})
    server.qso_patch(sandbox_id, "qso://demo/object", {"tick": 1})

    with pytest.raises(RuntimeError, match="rate limit"):
        server.qso_patch(sandbox_id, "qso://demo/object", {"tick": 2})


def test_apc_bootstrap_bundle_creates_run_manifest(tmp_path: Path) -> None:
    server = QSOEduMCPServer(
        state_root=tmp_path / "sandboxes",
        apc_state_root=tmp_path / "apc_runs",
    )
    sandbox_id = server.create_sandbox("apc-session")["sandbox_id"]

    bundle = server.qso_edu_apc_bootstrap(sandbox_id, mode="quick", owner="unit-test")
    result = bundle["result"]
    assert result["mode"] == "quick"
    run_path = Path(result["run_path"])
    assert run_path.exists()
    assert (run_path / "manifest.json").exists()
    assert (run_path / "validation" / "apc_bayes_comparison_latest.json").exists()
    assert "bayes_factor_summary" in result

    runs = server.qso_edu_apc_runs(sandbox_id)
    assert runs["result"]["runs"]
