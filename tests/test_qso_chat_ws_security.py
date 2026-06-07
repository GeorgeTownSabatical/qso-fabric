from __future__ import annotations

import pytest

from solis.identity.pq_keys import nist_primitives_available
from tools.qso_chat_ws import _build_anchor_ledger, _build_parser, _build_signer, _validate_requirements


def test_qso_chat_ws_parser_defaults_are_backward_compatible() -> None:
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8766
    assert args.itensor_filter is False
    assert _build_signer(args) is None
    assert _build_anchor_ledger(args) is None


def test_qso_chat_ws_builds_signer_from_seed_hex() -> None:
    if not nist_primitives_available():
        pytest.skip("liboqs ML-KEM/ML-DSA primitives are not available in this environment")

    parser = _build_parser()
    args = parser.parse_args(["--pq-seed-hex", "cd" * 32])
    signer = _build_signer(args)
    assert signer is not None
    envelope = signer.sign_payload({"k": "v"})
    assert envelope["signature_algo"] == "ML-DSA-65"


def test_qso_chat_ws_builds_local_anchor_ledger() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--anchor-contract-address", "0xabc"])
    ledger = _build_anchor_ledger(args)
    assert ledger is not None
    receipt = ledger.anchor_payload({"x": 1})
    assert receipt.mode == "local_deterministic"


def test_qso_chat_ws_fail_closed_requirements_block_missing_config() -> None:
    parser = _build_parser()

    args = parser.parse_args(["--require-tls"])
    with pytest.raises(SystemExit):
        _validate_requirements(args, signer=None, anchor_ledger=None)

    args = parser.parse_args(["--require-auth"])
    with pytest.raises(SystemExit):
        _validate_requirements(args, signer=None, anchor_ledger=None)

    args = parser.parse_args(["--require-quantum-envelope"])
    with pytest.raises(SystemExit):
        _validate_requirements(args, signer=None, anchor_ledger=None)

    args = parser.parse_args(["--require-contract-anchor"])
    with pytest.raises(SystemExit):
        _validate_requirements(args, signer=None, anchor_ledger=None)
