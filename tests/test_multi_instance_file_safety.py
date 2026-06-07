from __future__ import annotations

from pathlib import Path

from mcp_qso_edu.conversation_bridge import ConversationBridge
from mcp_qso_edu.sandbox_persistence import SandboxOperationStore
from services.transport.audit_logger import NetworkAuditLogger
from storage.event_store import JsonlEventStore


def test_jsonl_event_store_chain_with_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store_a = JsonlEventStore(path)
    store_b = JsonlEventStore(path)

    store_a.append(
        {
            "event_id": "evt-a",
            "timestamp": "2026-03-01T00:00:00+00:00",
            "actor": "node-a",
            "object_uri": "qso://mesh/demo",
            "delta": {"n": 1},
            "signature": "sig-a",
            "policy_version": "v1",
            "node_id": "node-a",
        }
    )
    store_b.append(
        {
            "event_id": "evt-b",
            "timestamp": "2026-03-01T00:00:01+00:00",
            "actor": "node-b",
            "object_uri": "qso://mesh/demo",
            "delta": {"n": 2},
            "signature": "sig-b",
            "policy_version": "v1",
            "node_id": "node-b",
        }
    )

    rows = JsonlEventStore(path).all()
    assert len(rows) == 2
    assert rows[1]["prev_hash"] == rows[0]["hash"]
    assert JsonlEventStore(path).verify_chain() is True


def test_network_audit_logger_chain_with_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "network_audit.jsonl"
    logger_a = NetworkAuditLogger(path)
    logger_b = NetworkAuditLogger(path)

    first = logger_a.log(
        actor="node-a",
        object_uri="qso://infra.transport",
        payload={"mode": "direct"},
        kind="transport_mode_switch",
        policy_version="v1",
    )
    second = logger_b.log(
        actor="node-b",
        object_uri="qso://infra.transport",
        payload={"mode": "vpn"},
        kind="transport_mode_switch",
        policy_version="v1",
    )

    assert second["prev_hash"] == first["hash"]
    assert NetworkAuditLogger(path).verify_chain() is True


def test_conversation_bridge_append_with_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "plus_bridge.jsonl"
    bridge_a = ConversationBridge(path)
    bridge_b = ConversationBridge(path)

    first = bridge_a.append(source="chatgpt_plus", content="hello", session_id="shared")
    second = bridge_b.append(source="codex", content="ack", session_id="shared")

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert second["prev_hash"] == first["hash"]


def test_sandbox_operation_store_hash_chain_with_two_instances(tmp_path: Path) -> None:
    root = tmp_path / "sandboxes"
    store_a = SandboxOperationStore(root)
    store_b = SandboxOperationStore(root)
    sandbox_id = "mesh-sandbox"

    store_a.append_op(
        sandbox_id,
        {
            "op": "create",
            "uri": "qso://sandbox/mesh-sandbox/object",
            "schema": {"kind": "demo"},
        },
    )
    store_b.append_op(
        sandbox_id,
        {
            "op": "patch",
            "uri": "qso://sandbox/mesh-sandbox/object",
            "delta": {"status": "updated"},
            "actor": "node-b",
        },
    )

    rows = SandboxOperationStore(root).read_ops(sandbox_id)
    assert len(rows) == 2
    assert rows[0]["prev_hash"] == "GENESIS"
    assert rows[1]["prev_hash"] == rows[0]["hash"]
