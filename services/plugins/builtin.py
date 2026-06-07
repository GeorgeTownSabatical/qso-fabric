from __future__ import annotations

from typing import Any, Dict, List

from services.plugins.base import DemoNodeSpec


class QuantumSphereDemoPlugin:
    """Demo plugin that injects a rotating quantum-safe sphere node."""

    plugin_id = "quantum_sphere_demo"

    def manifest(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": "Quantum Sphere Demo",
            "version": "v1",
            "description": "Adds a multicolored rotating sphere with higher-dimensional and transaction-channel metadata.",
        }

    def nodes(self, *, world_uri: str) -> List[DemoNodeSpec]:
        root_uri = f"{world_uri.rstrip('/')}/node/root"
        sphere_uri = f"{world_uri.rstrip('/')}/node/quantum_sphere"
        beam_uri = f"{world_uri.rstrip('/')}/node/quantum_channel_beam"
        return [
            DemoNodeSpec(
                uri=sphere_uri,
                state={
                    "kind": "scene_node",
                    "id": "quantum_sphere",
                    "name": "QuantumSphere",
                    "parent": root_uri,
                    "transform": {"pos": [0.0, 1.8, -3.8], "rot": [0, 0, 0, 1], "scl": [1.25, 1.25, 1.25]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/sphere_quantum"},
                        "material": {"uri": "qso://asset/material/quantum_rainbow"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.6, -0.6, -0.6], "max": [0.6, 0.6, 0.6]},
                    "layer_mask": 1,
                    "meta": {
                        "higher_dimensions": 7,
                        "quantum_safe_channel": {
                            "scheme": "ML-KEM-768-demo",
                            "from": "qso://node/demo/a",
                            "to": "qso://node/demo/b",
                            "payload_type": "transaction_bundle",
                        },
                    },
                },
            ),
            DemoNodeSpec(
                uri=beam_uri,
                state={
                    "kind": "scene_node",
                    "id": "quantum_channel_beam",
                    "name": "QuantumChannelBeam",
                    "parent": sphere_uri,
                    "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [0.1, 0.1, 2.4]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/beam"},
                        "material": {"uri": "qso://asset/material/quantum_beam"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
                    "layer_mask": 1,
                },
            ),
        ]

    def animations(self, *, world_uri: str) -> List[Dict[str, Any]]:
        sphere_uri = f"{world_uri.rstrip('/')}/node/quantum_sphere"
        beam_uri = f"{world_uri.rstrip('/')}/node/quantum_channel_beam"
        return [
            {
                "uri": sphere_uri,
                "type": "spin",
                "axis": [0, 1, 0],
                "radians_per_sec": 0.85,
            },
            {
                "uri": beam_uri,
                "type": "spin",
                "axis": [0, 0, 1],
                "radians_per_sec": 1.35,
            },
        ]


class SatoshiChainDemoPlugin:
    """Demo plugin that injects a satoshi-chain anchor and ledger ring."""

    plugin_id = "satoshi_chain_demo"

    def manifest(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": "Satoshi Chain Demo",
            "version": "v1",
            "description": "Adds satoshi-chain scene nodes with sUTXO and snapshot metadata for qso_fabric demos.",
        }

    def nodes(self, *, world_uri: str) -> List[DemoNodeSpec]:
        root_uri = f"{world_uri.rstrip('/')}/node/root"
        anchor_uri = f"{world_uri.rstrip('/')}/node/satoshi_chain_anchor"
        ring_uri = f"{world_uri.rstrip('/')}/node/satoshi_chain_ledger_ring"
        return [
            DemoNodeSpec(
                uri=anchor_uri,
                state={
                    "kind": "scene_node",
                    "id": "satoshi_chain_anchor",
                    "name": "SatoshiChainAnchor",
                    "parent": root_uri,
                    "transform": {"pos": [2.4, 1.25, -3.1], "rot": [0, 0, 0, 1], "scl": [0.95, 0.95, 0.95]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/satoshi_anchor"},
                        "material": {"uri": "qso://asset/material/satoshi_gold"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.55, -0.55, -0.55], "max": [0.55, 0.55, 0.55]},
                    "layer_mask": 1,
                    "meta": {
                        "satoshi_chain": {
                            "chain_id": "SATOSHI_CHAIN_V1",
                            "snapshot_block": 840000,
                            "untouched_mode": "patoshi",
                            "token_model": "sUTXO_NFT",
                            "finality": "bft_deterministic",
                        }
                    },
                },
            ),
            DemoNodeSpec(
                uri=ring_uri,
                state={
                    "kind": "scene_node",
                    "id": "satoshi_chain_ledger_ring",
                    "name": "SatoshiChainLedgerRing",
                    "parent": anchor_uri,
                    "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [1.65, 0.09, 1.65]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/ledger_ring"},
                        "material": {"uri": "qso://asset/material/ledger_pulse"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.75, -0.1, -0.75], "max": [0.75, 0.1, 0.75]},
                    "layer_mask": 1,
                    "meta": {
                        "ledger_channel": {
                            "proof_mode": "spv_or_committee",
                            "asset_namespace": "qso://asset/sutxo",
                        }
                    },
                },
            ),
        ]

    def animations(self, *, world_uri: str) -> List[Dict[str, Any]]:
        anchor_uri = f"{world_uri.rstrip('/')}/node/satoshi_chain_anchor"
        ring_uri = f"{world_uri.rstrip('/')}/node/satoshi_chain_ledger_ring"
        return [
            {
                "uri": anchor_uri,
                "type": "spin",
                "axis": [0, 1, 0],
                "radians_per_sec": 0.52,
            },
            {
                "uri": ring_uri,
                "type": "spin",
                "axis": [1, 0, 0],
                "radians_per_sec": 0.34,
            },
        ]


class NLMDigitalCollectionsDemoPlugin:
    """Demo plugin that anchors NLM Digital Collections web-service metadata in QSO."""

    plugin_id = "nlm_digital_collections_demo"

    def manifest(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": "NLM Digital Collections Demo",
            "version": "v1",
            "description": "Adds NLM Digital Collections web-service endpoint/parameter metadata as QSO scene nodes.",
        }

    def nodes(self, *, world_uri: str) -> List[DemoNodeSpec]:
        root_uri = f"{world_uri.rstrip('/')}/node/root"
        anchor_uri = f"{world_uri.rstrip('/')}/node/nlm_dc_anchor"
        endpoint_uri = f"{world_uri.rstrip('/')}/node/nlm_dc_endpoint"
        return [
            DemoNodeSpec(
                uri=anchor_uri,
                state={
                    "kind": "scene_node",
                    "id": "nlm_dc_anchor",
                    "name": "NLMDigitalCollectionsAnchor",
                    "parent": root_uri,
                    "transform": {"pos": [-2.35, 1.4, -3.05], "rot": [0, 0, 0, 1], "scl": [1.0, 1.0, 1.0]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/data_anchor"},
                        "material": {"uri": "qso://asset/material/medical_blue"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.6, -0.6, -0.6], "max": [0.6, 0.6, 0.6]},
                    "layer_mask": 1,
                    "meta": {
                        "source": "National Library of Medicine Digital Collections",
                        "web_service": {
                            "base_url": "https://wsearch.nlm.nih.gov/ws/query",
                            "database": "digitalCollections",
                            "free_access": True,
                            "registration_required": False,
                            "request_rate_limit_per_minute": 85,
                            "cache_recommendation_hours": [12, 24],
                            "update_schedule": "weekly_sunday",
                        },
                    },
                },
            ),
            DemoNodeSpec(
                uri=endpoint_uri,
                state={
                    "kind": "scene_node",
                    "id": "nlm_dc_endpoint",
                    "name": "NLMDigitalCollectionsEndpoint",
                    "parent": anchor_uri,
                    "transform": {"pos": [0.0, -0.9, 0.0], "rot": [0, 0, 0, 1], "scl": [1.45, 0.2, 0.75]},
                    "components": {
                        "mesh": {"uri": "qso://asset/mesh/query_panel"},
                        "material": {"uri": "qso://asset/material/endpoint_panel"},
                    },
                    "bounds": {"type": "aabb", "min": [-0.7, -0.2, -0.4], "max": [0.7, 0.2, 0.4]},
                    "layer_mask": 1,
                    "meta": {
                        "query_contract": {
                            "required_initial_parameters": ["db", "term"],
                            "required_subsequent_parameters": ["file", "server", "retstart"],
                            "optional_parameters": ["retmax", "tool", "email"],
                            "db_required_value": "digitalCollections",
                            "field_prefix": "dc:<fieldValue>",
                            "publication_field": "Publication:<fieldValue>",
                            "response_root": "nlmSearchResult",
                            "response_format": "xml",
                        },
                        "dc_fields": [
                            "dc:creator",
                            "dc:coverage",
                            "dc:date",
                            "dc:description",
                            "dc:format",
                            "dc:identifier",
                            "dc:language",
                            "dc:relation",
                            "dc:rights",
                            "dc:subject",
                            "dc:title",
                            "dc:type",
                            "Publication",
                            "snippet",
                        ],
                    },
                },
            ),
        ]

    def animations(self, *, world_uri: str) -> List[Dict[str, Any]]:
        anchor_uri = f"{world_uri.rstrip('/')}/node/nlm_dc_anchor"
        endpoint_uri = f"{world_uri.rstrip('/')}/node/nlm_dc_endpoint"
        return [
            {
                "uri": anchor_uri,
                "type": "spin",
                "axis": [0, 1, 0],
                "radians_per_sec": 0.28,
            },
            {
                "uri": endpoint_uri,
                "type": "spin",
                "axis": [0, 0, 1],
                "radians_per_sec": 0.14,
            },
        ]
