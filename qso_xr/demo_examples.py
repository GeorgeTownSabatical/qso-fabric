from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from qso_xr.demo_schema import DemoExample, validate_demo_example

_DEMO_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "image_1_shadow_throne": {
        "title": "Shadow Throne Cinematic",
        "input_reference": "Image #1",
        "profile": "cinematic_low_light",
        "distinct_needs": [
            "atmospheric low-key lighting",
            "single focal character silhouette clarity",
            "high-contrast depth layering for distant sentinel figure",
            "slow camera drift with minimal UI overlay",
        ],
        "viewpoint": {"center": [0.0, 1.2, 4.5], "radius": 30.0, "layer_mask": 1},
        "nodes": [
            {
                "suffix": "throne_room",
                "patch": {
                    "id": "throne_room",
                    "transform": {"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [12.0, 8.0, 12.0]},
                    "bounds": {"min": [-6.0, -1.0, -6.0], "max": [6.0, 7.0, 6.0]},
                    "layer_mask": 1,
                    "components": {
                        "material": {"uri": "qso://mat.cinematic.obsidian"},
                    },
                    "render_hints": {"exposure": 0.35, "fog_density": 0.22, "palette": "deep_crimson_noir"},
                },
            },
            {
                "suffix": "queen_avatar",
                "patch": {
                    "id": "queen_avatar",
                    "parent": "",
                    "transform": {"pos": [0.0, 0.4, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [1.0, 1.0, 1.0]},
                    "bounds": {"min": [-0.5, 0.0, -0.5], "max": [0.5, 2.0, 0.5]},
                    "layer_mask": 1,
                    "components": {
                        "mesh": {"uri": "qso://mesh.avatar.regal_queen"},
                        "material": {"uri": "qso://mat.avatar.midnight_steel"},
                    },
                    "presence": {"pose": "seated_regal", "emotion": "controlled_dominance"},
                },
            },
            {
                "suffix": "sentinel_shadow",
                "patch": {
                    "id": "sentinel_shadow",
                    "transform": {"pos": [0.0, 2.2, -3.2], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [3.2, 3.2, 3.2]},
                    "bounds": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
                    "layer_mask": 1,
                    "components": {
                        "mesh": {"uri": "qso://mesh.entity.shadow_sentinel"},
                        "material": {"uri": "qso://mat.entity.void_black"},
                    },
                    "render_hints": {"rim_light": 0.08, "backglow": 0.18},
                },
            },
        ],
        "knowledge_claims": [
            {
                "section": "entity.throne_scene",
                "claim_id": "img1-c1",
                "statement": "Scene intent prioritizes mood and silhouette over geometric detail.",
                "confidence": 0.83,
            },
            {
                "section": "lighting.low_key",
                "claim_id": "img1-c2",
                "statement": "Low-key illumination with selective red accents drives visual hierarchy.",
                "confidence": 0.78,
            },
        ],
    },
    "image_2_torus_topology": {
        "title": "3D Substrate Topology Analytic",
        "input_reference": "Image #2",
        "profile": "analytic_educational",
        "distinct_needs": [
            "label readability and annotation anchoring",
            "geometry-first clarity for torus and defect overlays",
            "color-separable semantic channels (loops, fibers, leaks)",
            "fixed camera framing for reproducible analysis",
        ],
        "viewpoint": {"center": [0.0, 0.0, 0.0], "radius": 18.0, "layer_mask": 3},
        "nodes": [
            {
                "suffix": "torus_core",
                "patch": {
                    "id": "torus_core",
                    "transform": {"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [4.0, 4.0, 4.0]},
                    "bounds": {"min": [-2.0, -2.0, -2.0], "max": [2.0, 2.0, 2.0]},
                    "layer_mask": 1,
                    "components": {
                        "mesh": {"uri": "qso://mesh.math.torus"},
                        "material": {"uri": "qso://mat.math.translucent_substrate"},
                    },
                },
            },
            {
                "suffix": "cohomology_loops",
                "patch": {
                    "id": "cohomology_loops",
                    "parent": "",
                    "transform": {"pos": [0.0, 0.1, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [4.2, 4.2, 4.2]},
                    "bounds": {"min": [-2.2, -2.2, -2.2], "max": [2.2, 2.2, 2.2]},
                    "layer_mask": 2,
                    "components": {
                        "mesh": {"uri": "qso://mesh.math.loop_bundle"},
                        "material": {"uri": "qso://mat.math.purple_loop"},
                    },
                },
            },
            {
                "suffix": "annotation_panel",
                "patch": {
                    "id": "annotation_panel",
                    "transform": {"pos": [-5.2, 3.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scl": [2.4, 1.4, 0.2]},
                    "bounds": {"min": [-1.2, -0.7, -0.1], "max": [1.2, 0.7, 0.1]},
                    "layer_mask": 2,
                    "overlay": {
                        "title": "3D Substrate Vacuum Topology",
                        "bullets": [
                            "Torus mesh: substrate",
                            "Purple loops: cohomology classes",
                            "Blue arrows: local fibers",
                            "Black trails: non-Hermitian leaks",
                        ],
                    },
                },
            },
        ],
        "knowledge_claims": [
            {
                "section": "math.topology",
                "claim_id": "img2-c1",
                "statement": "Primary geometry is a torus substrate carrying loop and fiber overlays.",
                "confidence": 0.86,
            },
            {
                "section": "math.semantics",
                "claim_id": "img2-c2",
                "statement": "Color channels encode distinct structures requiring legend-preserving rendering.",
                "confidence": 0.9,
            },
        ],
    },
}


def list_demo_examples() -> List[str]:
    return sorted(_DEMO_EXAMPLES.keys())


def get_demo_example(name: str) -> DemoExample:
    key = str(name)
    if key not in _DEMO_EXAMPLES:
        raise KeyError(key)
    value = deepcopy(_DEMO_EXAMPLES[key])
    return validate_demo_example(value)
