from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Dict, List

from api.schemas.models import AuditQuery, QSOEvent
from services.crypto_access.service import CryptoAccessService
from services.event_log.signing import qso_event_payload
from storage.event_store import EventStore
from storage.indexing import EventIndex


class EventLogService:
    def __init__(
        self,
        crypto: CryptoAccessService | None = None,
        event_store: EventStore | None = None,
        index: EventIndex | None = None,
    ) -> None:
        self._events_by_uri: Dict[str, List[QSOEvent]] = defaultdict(list)
        self._rejected_events: Dict[str, List[QSOEvent]] = defaultdict(list)
        self.crypto = crypto
        self.event_store = event_store
        self.index = index
        self._bootstrap_from_store()

    def append(self, event: QSOEvent) -> None:
        self._events_by_uri[event.object_uri].append(event)
        if self.event_store is not None:
            self.event_store.append(event)
        if self.index is not None:
            self.index.add(event)

    def timeline(self, uri: str) -> List[QSOEvent]:
        return deepcopy(self._events_by_uri.get(uri, []))

    def replay(self, uri: str, strict: bool = True) -> List[QSOEvent]:
        events = sorted(
            self._events_by_uri.get(uri, []),
            key=lambda e: (e.timestamp.isoformat(), e.event_id, e.node_id),
        )

        verified: List[QSOEvent] = []
        for event in events:
            if self.crypto is None:
                verified.append(event)
                continue

            is_valid = self.crypto.verify(qso_event_payload(event), event.signature)
            if is_valid:
                verified.append(event)
                continue

            self._rejected_events[uri].append(event)
            if strict:
                raise ValueError(f"signature validation failed for event {event.event_id}")

        return deepcopy(verified)

    def rejected(self, uri: str) -> List[QSOEvent]:
        return deepcopy(self._rejected_events.get(uri, []))

    def rollback(self, uri: str, keep_events: int) -> List[QSOEvent]:
        if keep_events < 0:
            raise ValueError("keep_events must be >= 0")
        self._events_by_uri[uri] = self._events_by_uri.get(uri, [])[:keep_events]
        return self.timeline(uri)

    def audit(self, query: AuditQuery) -> List[QSOEvent]:
        pool: List[QSOEvent] = []
        if query.uri:
            pool = list(self._events_by_uri.get(query.uri, []))
        else:
            for events in self._events_by_uri.values():
                pool.extend(events)

        results: List[QSOEvent] = []
        for event in pool:
            if query.actor and event.actor != query.actor:
                continue
            if query.since and event.timestamp < query.since:
                continue
            results.append(event)
        return results

    def _bootstrap_from_store(self) -> None:
        if self.event_store is None:
            return
        try:
            rows = self.event_store.all()
        except Exception:
            return

        for row in rows:
            try:
                event = QSOEvent.model_validate(row)
            except Exception:
                continue
            self._events_by_uri[event.object_uri].append(event)
            if self.index is not None:
                self.index.add(event)
