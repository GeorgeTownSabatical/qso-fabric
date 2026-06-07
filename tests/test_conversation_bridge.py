from __future__ import annotations

from pathlib import Path

from mcp_qso_edu.conversation_bridge import ConversationBridge


def test_conversation_bridge_append_and_read(tmp_path: Path) -> None:
    path = tmp_path / "plus_bridge.jsonl"
    bridge = ConversationBridge(path)

    first = bridge.append(source="chatgpt_plus", content="hello", session_id="triad")
    second = bridge.append(source="codex", content="ack", session_id="triad")

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert second["prev_hash"] == first["hash"]

    read_all = bridge.read(after_seq=0, limit=10)
    assert len(read_all["messages"]) == 2
    assert read_all["next_seq"] == 2

    read_tail = bridge.read(after_seq=1, limit=10)
    assert len(read_tail["messages"]) == 1
    assert read_tail["messages"][0]["content"] == "ack"
