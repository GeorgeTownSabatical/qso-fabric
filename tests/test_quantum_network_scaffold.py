from __future__ import annotations

from services.runtime import QSOFabricRuntime
from tools.qso_quantum_fabric_demo import build_demo_report


def test_quantum_manager_execute_roundtrip() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://quantum.state/demo_job"

    runtime.state_engine.create_object(
        uri=uri,
        schema={"$id": "qso://quantum.network.object", "type": "quantum_network_object"},
    )
    runtime.state_engine.patch(
        uri=uri,
        delta={
            "backend": "qiskit",
            "qubit_count": 8,
            "circuit_spec": {"gates": [{"name": "h", "target": 0}]},
            "measurement_schema": {"shots": 256},
        },
        actor="test",
        policy_version="v1",
    )

    out = runtime.quantum.execute(uri=uri, actor="test", policy_version="v1")
    assert out["result"]["status"] == "completed"
    assert len(out["result"]["verification_hash"]) == 64

    replay = runtime.quantum_replay.replay(uri)
    assert replay["uri"] == uri
    assert replay["state"]["execution"]["status"] == "completed"


def test_quantum_manager_execute_fabric_roundtrip() -> None:
    runtime = QSOFabricRuntime()
    uri = "qso://quantum.fabric/demo_fabric"
    report = build_demo_report()

    runtime.state_engine.create_object(
        uri=uri,
        schema={"$id": "qso://quantum.network.object", "type": "quantum_network_object"},
    )
    runtime.state_engine.patch(
        uri=uri,
        delta={
            "object_kind": "fabric",
            "backend": "fabric_gluing",
            "coherence_threshold": 0.95,
            "fabric_payload": {
                "id": "fabric.demo",
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
                "metadata": {},
            },
        },
        actor="test",
        policy_version="v1",
    )

    out = runtime.quantum.execute(uri=uri, actor="test", policy_version="v1")
    assert out["result"]["backend"] == "fabric_gluing"
    assert out["result"]["status"] == "completed"
    assert out["result"]["fabric_report"]["healthy"] is True
    assert abs(out["result"]["fabric_report"]["global_coherence"] - report["global_coherence"]) < 1e-12

    replay = runtime.quantum_replay.replay(uri)
    assert replay["uri"] == uri
    assert replay["state"]["execution"]["backend"] == "fabric_gluing"
