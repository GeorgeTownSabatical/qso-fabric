from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List


class SubscriptionManager:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, uri: str, client_callback: Callable[[Any], None]) -> None:
        self._subs[uri].append(client_callback)

    def unsubscribe(self, uri: str, client_callback: Callable[[Any], None]) -> None:
        callbacks = self._subs.get(uri, [])
        if client_callback in callbacks:
            callbacks.remove(client_callback)
        if not callbacks and uri in self._subs:
            del self._subs[uri]

    def notify(self, uri: str, delta: Any) -> None:
        for cb in self._subs.get(uri, []):
            cb(delta)

    def notify_prefix(self, uri_prefix: str, payload_by_uri: Dict[str, Any]) -> None:
        for uri, payload in payload_by_uri.items():
            if uri.startswith(uri_prefix):
                self.notify(uri, payload)
