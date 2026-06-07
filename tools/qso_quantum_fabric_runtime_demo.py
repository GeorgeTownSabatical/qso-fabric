"""Persist and execute a fabric object through the QSO quantum runtime."""

from __future__ import annotations

import json

from api.mcp_tools.qso_tools import QSOMCPTools
from tools.qso_quantum_fabric_demo import build_demo_report


def _build_fabric_payload() -> dict[str, object]:
    report = build_demo_report()
    return {
        "id": "fabric.runtime.demo",
        "patches": {
            "patch.alpha": {
                "id": "patch.alpha",
                "domain": "sensor.alpha",
                "basis": ["|0>", "|1>"],
                "state": {
                    "id": "state.alpha",
                    "vector_real": [1.0, 1.0],
                    "vector_imag": [0.0, 0.0],
                    "phase": 0.0,
                    "uncertainty": 0.0,
                    "metadata": {},
                },
                "metadata": {},
            },
            "patch.beta": {
                "id": "patch.beta",
                "domain": "sensor.beta",
                "basis": ["|0>", "|1>"],
                "state": {
                    "id": "state.beta",
                    "vector_real": [0.99, 1.01],
                    "vector_imag": [0.0, 0.0],
                    "phase": 0.0,
                    "uncertainty": 0.0,
                    "metadata": {},
                },
                "metadata": {},
            },
        },
        "overlaps": {
            "overlap.alpha_beta": {
                "id": "overlap.alpha_beta",
                "patch_a": "patch.alpha",
                "patch_b": "patch.beta",
                "shared_domain": ["shared.coherence.window"],
                "restriction_a": {
                    "id": "restrict.alpha",
                    "source_patch": "patch.alpha",
                    "target_patch": "overlap.alpha_beta",
                    "projection_real": [[1.0, 0.0], [0.0, 1.0]],
                    "projection_imag": [[0.0, 0.0], [0.0, 0.0]],
                    "validation_rule": "dimension_match",
                    "metadata": {},
                },
                "restriction_b": {
                    "id": "restrict.beta",
                    "source_patch": "patch.beta",
                    "target_patch": "overlap.alpha_beta",
                    "projection_real": [[1.0, 0.0], [0.0, 1.0]],
                    "projection_imag": [[0.0, 0.0], [0.0, 0.0]],
                    "validation_rule": "dimension_match",
                    "metadata": {},
                },
                "metadata": {},
            }
        },
        "metadata": {"reference_global_coherence": report["global_coherence"]},
    }


def main() -> None:
    tools = QSOMCPTools()
    uri = "qso://quantum.fabric/demo_runtime"
    tools.qso_quantum_create(
        uri=uri,
        payload={
            "object_kind": "fabric",
            "backend": "fabric_gluing",
            "fabric_payload": _build_fabric_payload(),
            "coherence_threshold": 0.95,
            "verification_hash": "0" * 64,
        },
    )
    out = tools.qso_quantum_execute(uri)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
