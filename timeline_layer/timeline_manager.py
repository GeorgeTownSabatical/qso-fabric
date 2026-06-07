from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, List

from timeline_layer.event import TimelineEvent


class TimelineManager:
    def __init__(self) -> None:
        self.timeline: DefaultDict[str, List[TimelineEvent]] = defaultdict(list)

    def record_event(self, qso_uri: str, event: TimelineEvent) -> None:
        self.timeline[qso_uri].append(event)

    def get_timeline(self, qso_uri: str) -> List[TimelineEvent]:
        return list(self.timeline.get(qso_uri, []))

    def replay(self, qso_uri: str) -> List[TimelineEvent]:
        return self.get_timeline(qso_uri)
