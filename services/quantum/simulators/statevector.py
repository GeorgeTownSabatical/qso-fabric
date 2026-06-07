from __future__ import annotations

import cmath
import math
from typing import Any

from services.quantum.models import QuantumJob
from solis.shared.hashing import sha256_hex_obj


def _apply_single_qubit_gate(state: list[complex], target: int, matrix: tuple[complex, complex, complex, complex]) -> None:
    stride = 1 << target
    period = stride << 1
    for start in range(0, len(state), period):
        for offset in range(stride):
            zero_idx = start + offset
            one_idx = zero_idx + stride
            a0 = state[zero_idx]
            a1 = state[one_idx]
            state[zero_idx] = matrix[0] * a0 + matrix[1] * a1
            state[one_idx] = matrix[2] * a0 + matrix[3] * a1


def _apply_controlled_x(state: list[complex], control: int, target: int) -> None:
    if control == target:
        raise ValueError("control and target must differ")
    for basis in range(len(state)):
        control_on = (basis >> control) & 1
        target_on = (basis >> target) & 1
        if control_on and not target_on:
            partner = basis | (1 << target)
            state[basis], state[partner] = state[partner], state[basis]


def _apply_controlled_z(state: list[complex], control: int, target: int) -> None:
    if control == target:
        raise ValueError("control and target must differ")
    for basis in range(len(state)):
        if ((basis >> control) & 1) and ((basis >> target) & 1):
            state[basis] *= -1


def _single_qubit_matrix(name: str) -> tuple[complex, complex, complex, complex]:
    inv_sqrt2 = 1 / math.sqrt(2)
    matrices: dict[str, tuple[complex, complex, complex, complex]] = {
        "i": (1, 0, 0, 1),
        "x": (0, 1, 1, 0),
        "y": (0, -1j, 1j, 0),
        "z": (1, 0, 0, -1),
        "h": (inv_sqrt2, inv_sqrt2, inv_sqrt2, -inv_sqrt2),
        "s": (1, 0, 0, 1j),
        "t": (1, 0, 0, cmath.exp(1j * math.pi / 4)),
    }
    try:
        return matrices[name]
    except KeyError as exc:
        raise ValueError(f"unsupported gate: {name}") from exc


def _normalize_gate_name(raw: Any) -> str:
    return str(raw).strip().lower().replace("-", "")


def _qubit_index(raw: Any, *, field: str) -> int:
    value = int(raw)
    if value < 0:
        raise ValueError(f"{field} must be >= 0")
    return value


def _bitstring(index: int, qubit_count: int) -> str:
    return format(index, f"0{qubit_count}b")


def _density_matrix_for_qubit(state: list[complex], qubit: int) -> list[list[complex]]:
    rho00 = 0j
    rho01 = 0j
    rho10 = 0j
    rho11 = 0j
    mask = 1 << qubit
    for basis in range(len(state)):
        if basis & mask:
            continue
        partner = basis | mask
        a0 = state[basis]
        a1 = state[partner]
        rho00 += a0 * a0.conjugate()
        rho01 += a0 * a1.conjugate()
        rho10 += a1 * a0.conjugate()
        rho11 += a1 * a1.conjugate()
    return [[rho00, rho01], [rho10, rho11]]


def _entropy_from_density_matrix(rho: list[list[complex]]) -> float:
    trace = (rho[0][0] + rho[1][1]).real
    determinant = (rho[0][0] * rho[1][1] - rho[0][1] * rho[1][0]).real
    discriminant = max(0.0, trace * trace - 4.0 * determinant)
    root = math.sqrt(discriminant)
    eigenvalues = [max(0.0, min(1.0, (trace + root) / 2.0)), max(0.0, min(1.0, (trace - root) / 2.0))]
    entropy = 0.0
    for value in eigenvalues:
        if value > 1e-12:
            entropy -= value * math.log2(value)
    return entropy


def _measurement_counts(probabilities: list[float], shots: int) -> dict[str, int]:
    scaled = [prob * shots for prob in probabilities]
    counts = [int(math.floor(value)) for value in scaled]
    remainder = shots - sum(counts)
    order = sorted(range(len(probabilities)), key=lambda idx: (scaled[idx] - counts[idx], probabilities[idx]), reverse=True)
    for idx in order[:remainder]:
        counts[idx] += 1
    return {str(idx): count for idx, count in enumerate(counts) if count > 0}


def simulate_quantum_job(job: QuantumJob) -> dict[str, Any]:
    if job.qubit_count < 1:
        raise ValueError("qubit_count must be >= 1")
    if job.qubit_count > 12:
        raise ValueError("builtin simulator caps qubit_count at 12")

    state = [0j] * (1 << job.qubit_count)
    state[0] = 1 + 0j
    entangling_pairs: set[tuple[int, int]] = set()

    for gate in list(job.circuit_spec.get("gates", [])):
        if not isinstance(gate, dict):
            raise TypeError("gate entries must be objects")
        name = _normalize_gate_name(gate.get("name", ""))
        if name in {"cx", "cnot"}:
            control = _qubit_index(gate.get("control"), field="control")
            target = _qubit_index(gate.get("target"), field="target")
            _apply_controlled_x(state, control, target)
            entangling_pairs.add(tuple(sorted((control, target))))
            continue
        if name == "cz":
            control = _qubit_index(gate.get("control"), field="control")
            target = _qubit_index(gate.get("target"), field="target")
            _apply_controlled_z(state, control, target)
            entangling_pairs.add(tuple(sorted((control, target))))
            continue
        target = _qubit_index(gate.get("target"), field="target")
        _apply_single_qubit_gate(state, target, _single_qubit_matrix(name))

    probabilities = [abs(amplitude) ** 2 for amplitude in state]
    shots = int(job.measurement_schema.get("shots", 1024))
    counts_by_index = _measurement_counts(probabilities, shots)
    counts = {_bitstring(int(idx), job.qubit_count): value for idx, value in counts_by_index.items()}
    most_likely_idx = max(range(len(probabilities)), key=lambda idx: probabilities[idx])

    entropies = []
    for qubit in range(job.qubit_count):
        rho = _density_matrix_for_qubit(state, qubit)
        entropies.append({"qubit": qubit, "entropy": round(_entropy_from_density_matrix(rho), 8)})

    logical_graph = [
        {
            "source": left,
            "target": right,
            "relationship": "entangled_gate_path",
            "score": round((entropies[left]["entropy"] + entropies[right]["entropy"]) / 2.0, 8),
        }
        for left, right in sorted(entangling_pairs)
    ]
    amplitudes = []
    for idx, amplitude in enumerate(state):
        if abs(amplitude) > 1e-9:
            amplitudes.append(
                {
                    "basis": _bitstring(idx, job.qubit_count),
                    "real": round(amplitude.real, 8),
                    "imag": round(amplitude.imag, 8),
                }
            )

    measurement_results = {
        "counts": counts,
        "shots": shots,
        "most_likely_bitstring": _bitstring(most_likely_idx, job.qubit_count),
        "qubit_entropies": entropies,
        "logical_entanglement_graph": logical_graph,
        "nonzero_amplitudes": amplitudes,
    }
    noise_profile = {"model": "ideal_statevector", "backend": "builtin"}
    execution_proof = {
        "engine": "builtin_statevector_fallback",
        "gate_count": len(list(job.circuit_spec.get("gates", []))),
        "circuit_hash": sha256_hex_obj(job.circuit_spec),
    }
    verification_hash = sha256_hex_obj(
        {
            "uri": job.uri,
            "backend": job.backend,
            "measurement_results": measurement_results,
            "execution_proof": execution_proof,
        }
    )
    return {
        "measurement_results": measurement_results,
        "noise_profile": noise_profile,
        "execution_proof": execution_proof,
        "verification_hash": verification_hash,
    }
