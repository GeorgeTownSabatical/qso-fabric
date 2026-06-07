from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUE_VALUES


def _parse_opt_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_float(value: str | None, *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ZKCommandConfig:
    enabled: bool = False
    circuit_path: str | None = None
    artifacts_dir: str | None = None
    zkey_path: str | None = None
    verification_key_path: str | None = None
    wasm_path: str | None = None
    circom_bin: str = "circom"
    snarkjs_bin: str = "snarkjs"
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ZKCommandConfig":
        source = os.environ if env is None else env
        return cls(
            enabled=_parse_bool(source.get("SOLIS_ZK_ENABLE_COMMANDS")),
            circuit_path=_parse_opt_str(source.get("SOLIS_ZK_CIRCUIT_PATH")),
            artifacts_dir=_parse_opt_str(source.get("SOLIS_ZK_ARTIFACTS_DIR")),
            zkey_path=_parse_opt_str(source.get("SOLIS_ZK_ZKEY_PATH")),
            verification_key_path=_parse_opt_str(source.get("SOLIS_ZK_VERIFICATION_KEY_PATH")),
            wasm_path=_parse_opt_str(source.get("SOLIS_ZK_WASM_PATH")),
            circom_bin=_parse_opt_str(source.get("SOLIS_ZK_CIRCOM_BIN")) or "circom",
            snarkjs_bin=_parse_opt_str(source.get("SOLIS_ZK_SNARKJS_BIN")) or "snarkjs",
            timeout_seconds=_parse_float(
                source.get("SOLIS_ZK_COMMAND_TIMEOUT_SECONDS"),
                default=60.0,
            ),
        )


class CircomSnarkjsAdapter:
    def __init__(self, config: ZKCommandConfig | None = None):
        self.config = config or ZKCommandConfig.from_env()

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
        )

    def prove(
        self,
        *,
        epoch: int,
        entropy: float,
        magnetic: float,
        fusion: float,
    ) -> dict[str, str] | None:
        if not self.config.enabled:
            return None
        if not self.config.circuit_path or not self.config.artifacts_dir or not self.config.zkey_path:
            return None

        circuit_path = Path(self.config.circuit_path)
        artifacts_dir = Path(self.config.artifacts_dir)
        circuit_stem = circuit_path.stem
        wasm_path = (
            Path(self.config.wasm_path)
            if self.config.wasm_path
            else artifacts_dir / f"{circuit_stem}_js" / f"{circuit_stem}.wasm"
        )
        input_path = artifacts_dir / f"collapse_input_{epoch}.json"
        proof_path = artifacts_dir / f"proof_{epoch}.json"
        public_signals_path = artifacts_dir / f"public_{epoch}.json"

        try:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            input_payload = {
                "entropy": entropy,
                "magnetic": magnetic,
                "fusion": fusion,
            }
            input_path.write_text(
                json.dumps(input_payload, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )

            circom_result = self._run(
                [
                    self.config.circom_bin,
                    str(circuit_path),
                    "--r1cs",
                    "--wasm",
                    "--sym",
                    "-o",
                    str(artifacts_dir),
                ]
            )
            if circom_result.returncode != 0:
                return None

            snarkjs_result = self._run(
                [
                    self.config.snarkjs_bin,
                    "groth16",
                    "fullprove",
                    str(input_path),
                    str(wasm_path),
                    str(self.config.zkey_path),
                    str(proof_path),
                    str(public_signals_path),
                ]
            )
            if snarkjs_result.returncode != 0:
                return None
        except (OSError, subprocess.SubprocessError):
            return None

        return {
            "circuit_path": str(circuit_path),
            "artifacts_dir": str(artifacts_dir),
            "input_path": str(input_path),
            "wasm_path": str(wasm_path),
            "zkey_path": str(self.config.zkey_path),
            "proof_path": str(proof_path),
            "public_signals_path": str(public_signals_path),
        }

    def verify(self, proof: Mapping[str, Any]) -> bool | None:
        if not self.config.enabled or not self.config.verification_key_path:
            return None

        artifacts = proof.get("artifacts")
        if not isinstance(artifacts, Mapping):
            return None

        proof_path = artifacts.get("proof_path")
        public_signals_path = artifacts.get("public_signals_path")
        if not isinstance(proof_path, str) or not isinstance(public_signals_path, str):
            return None

        try:
            result = self._run(
                [
                    self.config.snarkjs_bin,
                    "groth16",
                    "verify",
                    str(self.config.verification_key_path),
                    public_signals_path,
                    proof_path,
                ]
            )
        except (OSError, subprocess.SubprocessError):
            return None

        return result.returncode == 0
