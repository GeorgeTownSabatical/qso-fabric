from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StreamSubscriber:
    queue: asyncio.Queue[dict[str, Any]]


class TransportWebsocketStream:
    def __init__(self, queue_size: int = 256) -> None:
        self._queue_size = max(1, int(queue_size))
        self._subscribers: list[StreamSubscriber] = []

    def subscribe(self) -> StreamSubscriber:
        subscriber = StreamSubscriber(queue=asyncio.Queue(maxsize=self._queue_size))
        self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: StreamSubscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    async def publish(self, payload: dict[str, Any]) -> None:
        stale: list[StreamSubscriber] = []
        for subscriber in list(self._subscribers):
            try:
                subscriber.queue.put_nowait(dict(payload))
            except asyncio.QueueFull:
                try:
                    _ = subscriber.queue.get_nowait()
                    subscriber.queue.put_nowait(dict(payload))
                except Exception:
                    stale.append(subscriber)
        for subscriber in stale:
            self.unsubscribe(subscriber)

    async def stream(self, subscriber: StreamSubscriber):
        try:
            while True:
                payload = await subscriber.queue.get()
                yield payload
        finally:
            self.unsubscribe(subscriber)
