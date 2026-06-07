from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


class QSOWebSocketGateway:
    """Async websocket-friendly adapters for QSO streams."""

    def __init__(self, tools: QSOMCPTools | None = None) -> None:
        self.tools = tools or QSOMCPTools()

    async def stream_uri(
        self,
        uri: str,
        *,
        cursor: int | str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
        include_replay: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        stream = self.tools.qso_subscribe(
            uri=uri,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
            include_replay=include_replay,
        )
        async for payload in stream:
            yield {"type": "qso.event", "payload": payload}

    async def stream_prefix(
        self,
        uri_prefix: str,
        *,
        cursor: str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        stream = self.tools.qso_subscribe_prefix(
            uri_prefix=uri_prefix,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
        async for payload in stream:
            yield {"type": "qso.prefix_event", "payload": payload}

    async def stream_projection(
        self,
        uri: str,
        *,
        viewpoint: Dict[str, Any] | None = None,
        radius: float = 150.0,
        cursor: int | str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        stream = self.tools.qso_subscribe_projection(
            uri=uri,
            viewpoint=viewpoint,
            radius=radius,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
        async for payload in stream:
            yield {"type": "qso.projection", "payload": payload}

    async def stream_scene_render_v1(
        self,
        world_uri: str,
        *,
        viewpoint: Dict[str, Any] | None = None,
        cursor: str | None = None,
        backpressure: str = "drop_oldest",
        queue_size: int = 256,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        stream = self.tools.qso_subscribe_scene_render_v1(
            world_uri=world_uri,
            viewpoint=viewpoint,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
        async for payload in stream:
            yield {"type": "qso.scene_render_v1", "payload": payload}

    @staticmethod
    def encode_packet(packet: Dict[str, Any]) -> str:
        return json.dumps(packet, sort_keys=True, separators=(",", ":"))
