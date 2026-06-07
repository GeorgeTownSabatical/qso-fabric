from __future__ import annotations

import base64
import hashlib
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_KEY_PREFIX = "pqv2:"
_SIG_PREFIX = "pqsigv2:"


@dataclass(frozen=True)
class PQKeyPair:
    signature_algo: str
    kem_algo: str
    public_key: str
    private_key: str


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64d(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw.encode("ascii"))


def _has_liboqs(install_path: str) -> bool:
    root = Path(install_path).expanduser()
    lib_dir = root / "lib"
    if not lib_dir.exists():
        return False
    patterns = ("liboqs*.dylib", "liboqs*.so", "liboqs*.dll")
    return any(any(lib_dir.glob(pattern)) for pattern in patterns)


def _candidate_oqs_paths() -> list[str]:
    candidates = []
    for env_name in ("OQS_INSTALL_PATH", "QSO_PQ_OQS_INSTALL_PATH", "QSO_CHAT_WS_OQS_INSTALL_PATH"):
        configured = os.getenv(env_name, "").strip()
        if configured:
            candidates.append(configured)
    candidates.extend(
        [
            "/opt/homebrew",
            "/usr/local",
            "/usr",
        ]
    )
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
    return out


def _resolve_oqs_install_path() -> str | None:
    for candidate in _candidate_oqs_paths():
        if _has_liboqs(candidate):
            return candidate
    return None


def _require_oqs() -> Any:
    # Fail closed; no implicit runtime installation allowed.
    install_path = _resolve_oqs_install_path()
    if install_path is None:
        raise RuntimeError(
            "liboqs runtime not found. Install liboqs and set OQS_INSTALL_PATH "
            "(or QSO_PQ_OQS_INSTALL_PATH / QSO_CHAT_WS_OQS_INSTALL_PATH)."
        )
    os.environ["OQS_INSTALL_PATH"] = install_path
    return importlib.import_module("oqs")


def nist_primitives_available(signature_algo: str = "ML-DSA-65", kem_algo: str = "ML-KEM-768") -> bool:
    try:
        oqs = _require_oqs()
        return (
            signature_algo in oqs.get_enabled_sig_mechanisms()
            and kem_algo in oqs.get_enabled_kem_mechanisms()
        )
    except Exception:
        return False


def _encode_key_bundle(payload: dict[str, Any]) -> str:
    return _KEY_PREFIX + _b64e(_canonical_json(payload).encode("utf-8"))


def _decode_key_bundle(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text.startswith(_KEY_PREFIX):
        return None
    encoded = text[len(_KEY_PREFIX) :]
    try:
        payload = json.loads(_b64d(encoded).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid pqv2 key bundle") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid pqv2 key bundle")
    return payload


def _encode_sig_bundle(payload: dict[str, Any]) -> str:
    return _SIG_PREFIX + _b64e(_canonical_json(payload).encode("utf-8"))


def _decode_sig_bundle(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text.startswith(_SIG_PREFIX):
        return None
    encoded = text[len(_SIG_PREFIX) :]
    try:
        payload = json.loads(_b64d(encoded).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid pqsigv2 signature bundle") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid pqsigv2 signature bundle")
    return payload


def generate_keypair(seed: bytes, *, signature_algo: str = "ML-DSA-65", kem_algo: str = "ML-KEM-768") -> PQKeyPair:
    if not isinstance(seed, (bytes, bytearray)) or len(seed) < 16:
        raise ValueError("seed must be bytes and length >= 16")

    oqs = _require_oqs()
    if signature_algo not in oqs.get_enabled_sig_mechanisms():
        raise ValueError(f"signature algorithm not enabled in liboqs: {signature_algo}")
    if kem_algo not in oqs.get_enabled_kem_mechanisms():
        raise ValueError(f"KEM algorithm not enabled in liboqs: {kem_algo}")

    with oqs.Signature(signature_algo) as sig_obj:
        signature_public_key = bytes(sig_obj.generate_keypair())
        signature_secret_key = bytes(sig_obj.export_secret_key())

    with oqs.KeyEncapsulation(kem_algo) as kem_obj:
        seed_material = hashlib.sha3_512(bytes(seed) + b":kem").digest()
        if hasattr(kem_obj, "length_keypair_seed"):
            needed = int(getattr(kem_obj, "length_keypair_seed"))
            repeats = (needed // len(seed_material)) + 1
            kem_seed = (seed_material * repeats)[:needed]
            kem_public_key = bytes(kem_obj.generate_keypair_seed(kem_seed))
        else:
            kem_public_key = bytes(kem_obj.generate_keypair())
        kem_secret_key = bytes(kem_obj.export_secret_key())

    public = _encode_key_bundle(
        {
            "v": 2,
            "signature_algo": signature_algo,
            "kem_algo": kem_algo,
            "signature_public_key_b64": _b64e(signature_public_key),
            "kem_public_key_b64": _b64e(kem_public_key),
        }
    )
    private = _encode_key_bundle(
        {
            "v": 2,
            "signature_algo": signature_algo,
            "kem_algo": kem_algo,
            "signature_public_key_b64": _b64e(signature_public_key),
            "signature_secret_key_b64": _b64e(signature_secret_key),
            "kem_public_key_b64": _b64e(kem_public_key),
            "kem_secret_key_b64": _b64e(kem_secret_key),
        }
    )

    return PQKeyPair(
        signature_algo=signature_algo,
        kem_algo=kem_algo,
        public_key=public,
        private_key=private,
    )


def sign(message: bytes, private_key_hex: str) -> str:
    bundle = _decode_key_bundle(private_key_hex)
    if bundle is None:
        raise ValueError("legacy signing keys are blocked; rotate to pqv2 key bundles")

    oqs = _require_oqs()
    signature_algo = str(bundle.get("signature_algo", "")).strip()
    if not signature_algo:
        raise ValueError("missing signature_algo in pqv2 key bundle")
    signature_secret_key = _b64d(str(bundle.get("signature_secret_key_b64", "")))
    with oqs.Signature(signature_algo, secret_key=signature_secret_key) as sig_obj:
        signature = bytes(sig_obj.sign(message))
    return _encode_sig_bundle(
        {
            "v": 2,
            "signature_algo": signature_algo,
            "signature_b64": _b64e(signature),
        }
    )


def verify(message: bytes, signature_hex: str, private_key_hex: str) -> bool:
    bundle = _decode_key_bundle(private_key_hex)
    if bundle is None:
        return False

    sig_bundle = _decode_sig_bundle(signature_hex)
    if sig_bundle is None:
        return False
    if int(sig_bundle.get("v", 0)) != 2:
        return False

    signature_algo = str(bundle.get("signature_algo", "")).strip()
    if signature_algo != str(sig_bundle.get("signature_algo", "")).strip():
        return False
    signature_public_key = _b64d(str(bundle.get("signature_public_key_b64", "")))
    signature = _b64d(str(sig_bundle.get("signature_b64", "")))

    oqs = _require_oqs()
    signature_secret_key = _b64d(str(bundle.get("signature_secret_key_b64", "")))
    with oqs.Signature(signature_algo, secret_key=signature_secret_key) as sig_obj:
        return bool(sig_obj.verify(message, signature, signature_public_key))
