from __future__ import annotations

from copy import deepcopy
from typing import Any


class TutorialEngine:
    _EXPLANATIONS = {
        "create": "You created a sandboxed QSO object. Every mutation will emit replayable events.",
        "read": "You read a sandboxed QSO object. Reads are isolated per sandbox namespace.",
        "patch": "You applied an event-sourced patch. State changed through deterministic delta application.",
        "timeline": "You retrieved the event timeline. This is the replay backbone for deterministic audits.",
        "entangle": "You created an entanglement edge between sandbox objects.",
        "export_snapshot": "You exported a replayable snapshot blob for this sandbox object.",
        "subscribe": "You requested a live stream. Subscription output is scoped to sandbox URIs only.",
        "chat_open": "You opened a canonical sandbox conversation object.",
        "chat_init": "You initialized the canonical sandbox conversation object.",
        "chat_append": "You appended a message through an event-sourced chat delta.",
        "chat_read": "You read deterministic chat state from the conversation object.",
        "chat_tail": "You fetched the latest bounded message window for prompt context.",
        "chat_export_markdown": "You exported the conversation as deterministic markdown.",
        "chat_summarize": "You generated a deterministic rolling summary as a signed system message.",
        "chat_verify": "You audited message signatures and produced a deterministic integrity report.",
        "chat_fork": "You forked a conversation by copying a bounded message slice.",
        "chat_subscribe": "You subscribed to live updates for a conversation object.",
        "apc_bootstrap": "You generated a full APC educational development bundle with versioned artifacts.",
        "apc_runs": "You listed APC educational runs for this sandbox.",
        "apc_audit": "You generated a deterministic APC reproducible audit payload.",
        "apc_resources": "You loaded APC templates for checklists, scorecards, comparison, and red-team review.",
    }

    def annotate(self, action: str, result: Any) -> dict[str, Any]:
        return {
            "result": deepcopy(result),
            "explanation": self._EXPLANATIONS.get(action, "Sandbox action completed."),
            "action": action,
        }

    def tutorials(self) -> list[dict[str, str]]:
        return [
            {"step": "create", "summary": self._EXPLANATIONS["create"]},
            {"step": "patch", "summary": self._EXPLANATIONS["patch"]},
            {"step": "timeline", "summary": self._EXPLANATIONS["timeline"]},
            {"step": "entangle", "summary": self._EXPLANATIONS["entangle"]},
            {"step": "apc_bootstrap", "summary": self._EXPLANATIONS["apc_bootstrap"]},
            {"step": "apc_audit", "summary": self._EXPLANATIONS["apc_audit"]},
        ]
