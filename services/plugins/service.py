from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from services.plugins.base import DemoPlugin
from services.plugins.builtin import (
    NLMDigitalCollectionsDemoPlugin,
    QuantumSphereDemoPlugin,
    SatoshiChainDemoPlugin,
)


class PluginService:
    """Registry + application service for demo plugins."""

    def __init__(self, plugins: List[DemoPlugin] | None = None) -> None:
        self._plugins: List[DemoPlugin] = (
            list(plugins)
            if plugins is not None
            else [QuantumSphereDemoPlugin(), SatoshiChainDemoPlugin(), NLMDigitalCollectionsDemoPlugin()]
        )
        ids = [p.plugin_id for p in self._plugins]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate demo plugin ids are not allowed")

    def _resolve_plugins(self, plugin_ids: List[str] | None = None) -> List[DemoPlugin]:
        if not plugin_ids:
            return list(self._plugins)

        requested = [str(value).strip() for value in plugin_ids if str(value).strip()]
        if not requested:
            return list(self._plugins)

        requested = list(dict.fromkeys(requested))
        by_id = {plugin.plugin_id: plugin for plugin in self._plugins}
        missing = [plugin_id for plugin_id in requested if plugin_id not in by_id]
        if missing:
            raise ValueError(f"unknown demo plugin ids: {', '.join(missing)}")
        return [by_id[plugin_id] for plugin_id in requested]

    def list_demo_plugins(self, plugin_ids: List[str] | None = None) -> List[Dict[str, Any]]:
        return [deepcopy(p.manifest()) for p in self._resolve_plugins(plugin_ids)]

    def demo_payload(self, *, world_uri: str, plugin_ids: List[str] | None = None) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        animations: List[Dict[str, Any]] = []
        active_plugins = self._resolve_plugins(plugin_ids)
        for plugin in active_plugins:
            nodes.extend({"uri": node.uri, "state": deepcopy(node.state)} for node in plugin.nodes(world_uri=world_uri))
            animations.extend(deepcopy(anim) for anim in plugin.animations(world_uri=world_uri))
        return {
            "world_uri": world_uri,
            "plugins": [deepcopy(plugin.manifest()) for plugin in active_plugins],
            "nodes": nodes,
            "animations": animations,
        }

    def apply_demo_plugins(
        self,
        *,
        tools: Any,
        world_uri: str,
        actor: str = "scene-plugin",
        policy_version: str = "v1",
        node_id: str = "rest",
        plugin_ids: List[str] | None = None,
    ) -> Dict[str, Any]:
        payload = self.demo_payload(world_uri=world_uri, plugin_ids=plugin_ids)
        applied = 0
        for item in payload["nodes"]:
            uri = str(item["uri"])
            state = deepcopy(dict(item["state"]))
            try:
                tools.qso_create(uri=uri, schema={"type": "scene_node"})
            except Exception:
                pass
            tools.qso_patch(
                uri=uri,
                delta=state,
                actor=actor,
                policy_version=policy_version,
                node_id=node_id,
            )
            applied += 1
        return {
            "status": "ok",
            "world_uri": world_uri,
            "plugins": payload["plugins"],
            "animations": payload["animations"],
            "applied_nodes": applied,
        }
