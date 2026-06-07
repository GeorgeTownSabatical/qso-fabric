from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Mapping

from solis.constellation.contagion_graph import build_contagion_graph
from solis.hardening.rate_limit import RateLimiter
from solis.mcp_tools.solis_stream import SolisStream
from solis.projectors.stellar_projector_v1 import StellarState, project_stellar_v1
from solis.services.solis_constellation_service import SolisConstellationService
from solis.services.solis_meta_signal_service import SolisMetaSignalService
from solis.services.solis_star_service import SolisQSOBridge, SolisStarService


class SolisMCPTools:
    """MCP-style tool surface for Solis runtime."""

    def __init__(self, qso_bridge: SolisQSOBridge | None = None) -> None:
        self.qso_bridge = qso_bridge or SolisQSOBridge()
        self.star_service = SolisStarService(qso=self.qso_bridge)
        self.constellation_service = SolisConstellationService(star_service=self.star_service)
        self.meta_signal_service = SolisMetaSignalService(star_service=self.star_service)
        self.stream = SolisStream(getattr(self.qso_bridge, "tools", None))
        self.rate_limiter = RateLimiter(capacity=60, refill_per_sec=30.0)

    def create_star(
        self,
        star_id: str,
        chain_id: str,
        initial_state: Mapping[str, float] | None = None,
        caller: str = "global",
    ) -> Dict[str, Any]:
        self._guard(caller, "create_star")
        return self.star_service.create_star(star_id=star_id, chain_id=chain_id, initial_state=initial_state)

    def patch_star(
        self,
        star_uri_or_id: str,
        delta: Mapping[str, float],
        actor: str = "solis.mcp",
        relationship_event: Mapping[str, Any] | None = None,
        caller: str = "global",
    ) -> Dict[str, Any]:
        self._guard(caller, "patch_star")
        result = self.star_service.patch_star(
            star_uri_or_id=star_uri_or_id,
            delta=delta,
            actor=actor,
            relationship_event=relationship_event,
        )
        self.meta_signal_service.emit_signals(star_uri_or_id)
        return result

    def get_star(self, star_uri_or_id: str) -> Dict[str, Any]:
        return self.star_service.get_star(star_uri_or_id)

    def create_constellation(self, domain: str, star_uris: list[str], caller: str = "global") -> Dict[str, Any]:
        self._guard(caller, "create_constellation")
        constellation = self.constellation_service.create_constellation(domain=domain, star_uris=star_uris)
        graph = build_contagion_graph(star_uris)
        return {"constellation": constellation, "graph": graph}

    def project(self, star_uri_or_id: str, delta: Mapping[str, float]) -> Dict[str, Any]:
        current = self.star_service.get_star(star_uri_or_id).get("state_layer", {})
        state = StellarState.from_mapping(current)
        projected = project_stellar_v1(state, delta)
        return projected.as_dict()

    def timeline(self, star_uri_or_id: str, strict: bool = True) -> list[Dict[str, Any]]:
        return self.star_service.timeline(star_uri_or_id, strict=strict)

    def apply_policy(self, star_uri_or_id: str, policy: Mapping[str, Any], caller: str = "global") -> Dict[str, Any]:
        self._guard(caller, "apply_policy")
        return self.star_service.apply_policy_event(star_uri_or_id=star_uri_or_id, policy=policy)

    def apply_policy_from_uri(self, star_uri_or_id: str, policy_uri: str, caller: str = "global") -> Dict[str, Any]:
        self._guard(caller, "apply_policy_from_uri")
        payload = self.qso_bridge.read(policy_uri).get("state_layer", {})
        return self.star_service.apply_policy_event(star_uri_or_id=star_uri_or_id, policy=payload)

    def subscribe(
        self,
        uri_pattern: str = "qso://solis.star.*",
        cursor: str | None = None,
        backpressure: str = "block",
        queue_size: int = 512,
        strict: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        return self.stream.subscribe(
            uri_pattern=uri_pattern,
            cursor=cursor,
            backpressure=backpressure,
            queue_size=queue_size,
            strict=strict,
        )

    # MCP naming aliases
    def solis_create_star(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.create_star(*args, **kwargs)

    def solis_patch_star(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.patch_star(*args, **kwargs)

    def solis_get_star(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.get_star(*args, **kwargs)

    def solis_create_constellation(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.create_constellation(*args, **kwargs)

    def solis_project(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.project(*args, **kwargs)

    def solis_timeline(self, *args: Any, **kwargs: Any) -> list[Dict[str, Any]]:
        return self.timeline(*args, **kwargs)

    def solis_subscribe(self, *args: Any, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        return self.subscribe(*args, **kwargs)

    def solis_apply_policy(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.apply_policy(*args, **kwargs)

    def _guard(self, caller: str, method: str) -> None:
        key = f"{caller}:{method}"
        if not self.rate_limiter.allow(key):
            raise ValueError("rate limit exceeded")
