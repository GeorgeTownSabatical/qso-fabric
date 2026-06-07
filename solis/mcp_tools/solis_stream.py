from __future__ import annotations

from typing import Any, AsyncIterator, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


class SolisStream:
    def __init__(self, qso_tools: QSOMCPTools | None = None) -> None:
        self.qso_tools = qso_tools or QSOMCPTools()

    def subscribe(
        self,
        uri_pattern: str = "qso://solis.star.*",
        cursor: str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        if uri_pattern.endswith("*"):
            prefix = uri_pattern[:-1]
            return self.qso_tools.qso_subscribe_prefix(
                uri_prefix=prefix,
                cursor=cursor,
                backpressure=backpressure,
                queue_size=queue_size,
                strict=strict,
            )
        return self.qso_tools.qso_subscribe(
            uri=uri_pattern,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )
