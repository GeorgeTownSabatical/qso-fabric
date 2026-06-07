from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from solis.zk.command_adapter import ZKCommandConfig
from solis.zk.generate_proof import generate_collapse_proof
from solis.zk.verify_proof import verify_collapse_proof


def _run_checked(cmd: list[str]) -> None:
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise AssertionError(f"command failed: {' '.join(cmd)}\n{stderr}")


def _write_smoke_circuit(path: Path) -> None:
    path.write_text(
        (
            "pragma circom 2.1.6;\n"
            "template CollapseCheck() {\n"
            "  signal input entropy;\n"
            "  signal input magnetic;\n"
            "  signal input fusion;\n"
            "  signal output out;\n"
            "  out <== entropy + magnetic + fusion;\n"
            "}\n"
            "component main = CollapseCheck();\n"
        ),
        encoding="utf-8",
    )


@pytest.mark.zk_command_path
def test_command_path_smoke_with_real_toolchain(tmp_path: Path) -> None:
    if os.getenv("SOLIS_ZK_COMMAND_SMOKE") != "1":
        pytest.skip("set SOLIS_ZK_COMMAND_SMOKE=1 to run real command-path smoke")

    circom_bin = os.getenv("SOLIS_ZK_CIRCOM_BIN", "circom")
    snarkjs_bin = os.getenv("SOLIS_ZK_SNARKJS_BIN", "snarkjs")
    if shutil.which(circom_bin) is None or shutil.which(snarkjs_bin) is None:
        pytest.skip("circom/snarkjs binaries are not available on PATH")

    circuit_path = tmp_path / "collapse.circom"
    artifacts_dir = tmp_path / "artifacts"
    zkey_path = tmp_path / "phase2.zkey"
    verification_key_path = tmp_path / "verification_key.json"
    ptau_0 = tmp_path / "pot12_0000.ptau"
    ptau_1 = tmp_path / "pot12_0001.ptau"
    ptau_final = tmp_path / "pot12_final.ptau"

    _write_smoke_circuit(circuit_path)
    _run_checked(
        [
            circom_bin,
            str(circuit_path),
            "--r1cs",
            "--wasm",
            "--sym",
            "-o",
            str(artifacts_dir),
        ]
    )

    r1cs_path = artifacts_dir / "collapse.r1cs"
    assert r1cs_path.exists()

    _run_checked([snarkjs_bin, "powersoftau", "new", "bn128", "12", str(ptau_0)])
    _run_checked(
        [
            snarkjs_bin,
            "powersoftau",
            "contribute",
            str(ptau_0),
            str(ptau_1),
            "--name",
            "solis-ci-smoke",
            "-e",
            "solis-ci-smoke",
        ]
    )
    _run_checked([snarkjs_bin, "powersoftau", "prepare", "phase2", str(ptau_1), str(ptau_final)])
    _run_checked([snarkjs_bin, "groth16", "setup", str(r1cs_path), str(ptau_final), str(zkey_path)])
    _run_checked(
        [
            snarkjs_bin,
            "zkey",
            "export",
            "verificationkey",
            str(zkey_path),
            str(verification_key_path),
        ]
    )

    command_config = ZKCommandConfig(
        enabled=True,
        circuit_path=str(circuit_path),
        artifacts_dir=str(artifacts_dir),
        zkey_path=str(zkey_path),
        verification_key_path=str(verification_key_path),
        circom_bin=circom_bin,
        snarkjs_bin=snarkjs_bin,
        timeout_seconds=180.0,
    )

    proof = generate_collapse_proof(
        epoch=1,
        entropy=1.0,
        magnetic=0.0,
        fusion=1.0,
        threshold=1.0,
        command_config=command_config,
    )

    assert proof["scheme"] == "circom-snarkjs"
    assert verify_collapse_proof(proof, command_config=command_config)
