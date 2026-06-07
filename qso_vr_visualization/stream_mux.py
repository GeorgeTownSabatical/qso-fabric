from __future__ import annotations

from typing import Any, AsyncIterator, Dict

from qso_vr_visualization.interest_manager import InterestManager
from qso_vr_visualization.projection_compiler import ProjectionCompiler


class StreamMux:
    def __init__(self, interest_manager: InterestManager, compiler: ProjectionCompiler) -> None:
        self.interest_manager = interest_manager
        self.compiler = compiler

    async def stream(
        self,
        source: AsyncIterator[Dict[str, Any]],
        viewpoint: Dict[str, Any] | None = None,
        fallback_uri: str | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        async for payload in source:
            projection = self.compiler.compile(payload, fallback_uri=fallback_uri)
            if projection is None:
                continue

            uri = str(projection.get("uri", ""))
            if self.interest_manager.is_relevant(uri=uri, projection=projection, viewpoint=viewpoint):
                yield projection
