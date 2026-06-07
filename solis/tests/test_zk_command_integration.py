from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from solis.zk.command_adapter import ZKCommandConfig
from solis.zk.generate_proof import generate_collapse_proof
from solis.zk.verify_proof import verify_collapse_proof


def _build_command_config(tmp_path: Path) -> ZKCommandConfig:
    circuit_path = tmp_path / "collapse.circom"
    circuit_path.write_text("template CollapseCheck(){}", encoding="utf-8")
    return ZKCommandConfig(
        enabled=True,
        circuit_path=str(circuit_path),
        artifacts_dir=str(tmp_path / "artifacts"),
        zkey_path=str(tmp_path / "phase2.zkey"),
        verification_key_path=str(tmp_path / "verification_key.json"),
        circom_bin="circom-bin",
        snarkjs_bin="snarkjs-bin",
    )


def _generate_command_backed_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[dict[str, Any], ZKCommandConfig]:
    config = _build_command_config(tmp_path)

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("solis.zk.command_adapter.subprocess.run", fake_run)
    proof = generate_collapse_proof(
        epoch=42,
        entropy=0.41,
        magnetic=0.19,
        fusion=0.77,
        threshold=0.5,
        command_config=config,
    )
    return proof, config


def test_fallback_mode_remains_deterministic() -> None:
    proof = generate_collapse_proof(
        epoch=7,
        entropy=0.25,
        magnetic=0.15,
        fusion=0.9,
        threshold=0.5,
    )

    assert proof["scheme"] == "deterministic-hash-stub"
    assert "artifacts" not in proof
    assert verify_collapse_proof(proof)


def test_command_enabled_generation_uses_circom_and_snarkjs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    config = _build_command_config(tmp_path)

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("solis.zk.command_adapter.subprocess.run", fake_run)
    proof = generate_collapse_proof(
        epoch=5,
        entropy=0.4,
        magnetic=0.2,
        fusion=0.6,
        threshold=0.3,
        command_config=config,
    )

    assert proof["scheme"] == "circom-snarkjs"
    artifacts = proof["artifacts"]
    assert artifacts["circuit_path"] == config.circuit_path
    assert Path(artifacts["input_path"]).exists()
    assert calls[0][0] == "circom-bin"
    assert calls[1][:3] == ["snarkjs-bin", "groth16", "fullprove"]


def test_command_mode_verification_passes_on_snarkjs_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof, config = _generate_command_backed_proof(monkeypatch, tmp_path)

    def fake_verify_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("solis.zk.command_adapter.subprocess.run", fake_verify_run)
    assert verify_collapse_proof(proof, command_config=config)


def test_command_mode_verification_fails_on_snarkjs_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof, config = _generate_command_backed_proof(monkeypatch, tmp_path)

    def fake_verify_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr("solis.zk.command_adapter.subprocess.run", fake_verify_run)
    assert not verify_collapse_proof(proof, command_config=config)
