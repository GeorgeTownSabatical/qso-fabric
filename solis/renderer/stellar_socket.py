from __future__ import annotations

from typing import Any, AsyncIterator, Dict

from api.mcp_tools.qso_tools import QSOMCPTools


def stream_stellar_state(
    uri: str,
    *,
    qso_tools: QSOMCPTools | None = None,
    cursor: int | str | None = None,
) -> AsyncIterator[Dict[str, Any]]:
    tools = qso_tools or QSOMCPTools()
    return tools.qso_subscribe(uri=uri, cursor=cursor)
