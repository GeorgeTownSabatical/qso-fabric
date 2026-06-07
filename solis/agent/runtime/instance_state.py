from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentInstanceState:
    instance_id: str
    template_id: str
    owner_uri: str
    graph_hash: str
    events: list[dict[str, str]] = field(default_factory=list)

    def append_event(self, event_id: str, action: str) -> None:
        self.events.append({"event_id": event_id, "action": action})
