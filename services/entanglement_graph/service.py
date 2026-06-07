from __future__ import annotations

import asyncio
from contextlib import suppress
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Set

from api.schemas.models import EntanglementLink

BACKPRESSURE_MODES = {"block", "drop_oldest", "drop_newest"}


@dataclass
class _Subscriber:
    queue: asyncio.Queue[Dict[str, Any]]
    backpressure: str


class EntanglementGraphService:
    def __init__(self) -> None:
        self._links_by_source: Dict[str, List[EntanglementLink]] = defaultdict(list)
        self._subscribers: Dict[str, List[_Subscriber]] = defaultdict(list)

    def register_subscriber(
        self,
        uri: str,
        *,
        queue_size: int = 512,
        backpressure: str = "block",
        ready: asyncio.Event | None = None,
    ) -> _Subscriber:
        """Register a subscriber queue for a URI.

        Async generators only execute when iterated; this helper gives callers a
        deterministic way to activate a subscription before yielding replay.
        """

        mode = str(backpressure).lower()
        if mode not in {"block", "drop_oldest", "drop_newest"}:
            raise ValueError(f"unsupported backpressure mode: {backpressure}")

        subscriber = _Subscriber(queue=asyncio.Queue(maxsize=max(1, int(queue_size))), backpressure=mode)
        self._subscribers[uri].append(subscriber)
        if ready is not None:
            ready.set()
        return subscriber

    def unregister_subscriber(self, uri: str, subscriber: _Subscriber) -> None:
        subs = self._subscribers.get(uri)
        if not subs:
            return
        with suppress(ValueError):
            subs.remove(subscriber)
        if not subs:
            self._subscribers.pop(uri, None)

    def _has_path(self, src: str, dst: str, seen: Set[str] | None = None) -> bool:
        seen = seen or set()
        if src == dst:
            return True
        if src in seen:
            return False
        seen.add(src)
        for link in self._links_by_source.get(src, []):
            if self._has_path(link.target_uri, dst, seen):
                return True
        return False

    def entangle(self, link: EntanglementLink, allow_cycle: bool = False) -> None:
        if not allow_cycle and self._has_path(link.target_uri, link.source_uri):
            raise ValueError(f"entanglement link would create cycle: {link.source_uri} -> {link.target_uri}")

        self._links_by_source[link.source_uri].append(link)
        if link.bidirectional:
            if not allow_cycle:
                raise ValueError("bidirectional link rejected under DAG enforcement; use allow_cycle=True if explicitly required")
            reverse = EntanglementLink(
                source_uri=link.target_uri,
                target_uri=link.source_uri,
                relationship=link.relationship,
                strength=link.strength,
                sync_mode=link.sync_mode,
                latency_target_ms=link.latency_target_ms,
                bidirectional=False,
            )
            self._links_by_source[reverse.source_uri].append(reverse)

    def list_links(self, uri: str) -> List[EntanglementLink]:
        return deepcopy(self._links_by_source.get(uri, []))

    async def subscribe(
        self,
        uri: str,
        queue_size: int = 512,
        backpressure: str = "block",
        ready: asyncio.Event | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        if queue_size <= 0:
            raise ValueError("queue_size must be > 0")

        subscriber = self.register_subscriber(
            uri,
            queue_size=queue_size,
            backpressure=backpressure,
            ready=ready,
        )
        try:
            while True:
                event = await subscriber.queue.get()
                yield event
        finally:
            self.unregister_subscriber(uri, subscriber)

    async def _enqueue(self, subscriber: _Subscriber, payload: Dict[str, Any]) -> None:
        if subscriber.backpressure == "block":
            await subscriber.queue.put(payload)
            return

        if subscriber.backpressure == "drop_newest":
            if subscriber.queue.full():
                return
            subscriber.queue.put_nowait(payload)
            return

        # drop_oldest
        if subscriber.queue.full():
            try:
                subscriber.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        try:
            subscriber.queue.put_nowait(payload)
        except asyncio.QueueFull:
            return

    async def publish_patch(self, source_uri: str, payload: Dict[str, Any]) -> None:
        for subscriber in list(self._subscribers.get(source_uri, [])):
            await self._enqueue(subscriber, payload)

        for link in self._links_by_source.get(source_uri, []):
            enriched = {
                **payload,
                "entangled_from": source_uri,
                "relationship": link.relationship,
                "strength": link.strength,
                "sync_mode": link.sync_mode.value,
                "latency_target_ms": link.latency_target_ms,
            }
            for subscriber in list(self._subscribers.get(link.target_uri, [])):
                await self._enqueue(subscriber, enriched)
