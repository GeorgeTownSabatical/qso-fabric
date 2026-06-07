from __future__ import annotations

import asyncio
import argparse
import json
import os
from typing import Any

from mcp_qso_edu.protocol_server import QSOEduMCPProtocolServer
from services.quantum.response_filter import QuantumResponseFilter
from solis.hardening.quantum_socket import (
    QuantumSocketSigner,
    SolidityAnchorSocketLedger,
    build_tls_context,
)

try:
    import websockets
except ImportError as exc:  # pragma: no cover - runtime dependency path
    raise SystemExit("websockets package is required: pip install websockets") from exc


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


async def _serve(
    ws: Any,
    *,
    auth_token: str | None,
    signer: QuantumSocketSigner | None,
    anchor_ledger: SolidityAnchorSocketLedger | None,
    tls_enabled: bool,
    response_filter: QuantumResponseFilter | None,
    require_response_filter: bool,
) -> None:
    server = QSOEduMCPProtocolServer()
    async for message in ws:
        try:
            request = json.loads(message)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "invalid_json"}))
            continue

        if not isinstance(request, dict):
            await ws.send(json.dumps({"error": "invalid_message"}))
            continue

        if auth_token is not None and str(request.get("auth_token", "")).strip() != auth_token:
            await ws.send(json.dumps({"error": "unauthorized"}))
            continue

        request_type = str(request.get("type", "")).strip()
        if request_type == "handshake":
            payload: dict[str, Any] = {
                "ok": True,
                "transport": ("wss" if tls_enabled else "ws"),
                "auth_required": auth_token is not None,
                "quantum_envelope_enabled": signer is not None,
                "contract_anchor_enabled": anchor_ledger is not None,
            }
            if signer is not None:
                payload["crypto_profile_id"] = signer.crypto_profile_id
                payload["signature_algo"] = signer.signature_algo
                payload["kem_algo"] = signer.kem_algo
            await ws.send(json.dumps(payload, sort_keys=True))
            continue

        if request_type != "tail":
            await ws.send(json.dumps({"error": "unsupported_type", "supported_types": ["handshake", "tail"]}))
            continue

        if request.get("type") == "tail":
            session_token = str(request.get("session_token", request.get("sandbox_id", ""))).strip()
            if not session_token:
                await ws.send(json.dumps({"error": "session_token is required"}))
                continue
            sandbox = server.call_tool(
                "qso.create_sandbox",
                {"session_token": session_token},
            )
            sandbox_id = sandbox["sandbox_id"]
            server.call_tool(
                "qso.chat.init",
                {
                    "sandbox_id": sandbox_id,
                    "conversation_id": request.get("conversation_id", "main"),
                },
            )
            out = server.call_tool(
                "qso.chat.tail",
                {
                    "sandbox_id": sandbox_id,
                    "conversation_id": request.get("conversation_id", "main"),
                    "limit": int(request.get("limit", 20)),
                },
            )
            response_payload = dict(out) if isinstance(out, dict) else {"payload": out}
            response_payload["conversation_id"] = str(request.get("conversation_id", "main"))
            security_envelope: dict[str, Any] = {}

            signed_payload = {
                "type": "tail",
                "session_token": session_token,
                "conversation_id": str(request.get("conversation_id", "main")),
                "limit": int(request.get("limit", 20)),
                "payload": response_payload,
            }
            if signer is not None:
                security_envelope["quantum_envelope"] = signer.sign_payload(signed_payload)
            if anchor_ledger is not None:
                anchor_target = dict(signed_payload)
                if "quantum_envelope" in security_envelope:
                    anchor_target["quantum_envelope"] = security_envelope["quantum_envelope"]
                anchor_receipt = anchor_ledger.anchor_payload(anchor_target)
                security_envelope["contract_anchor"] = {
                    "contract_address": anchor_receipt.contract_address,
                    "merkle_root": anchor_receipt.merkle_root,
                    "tx_hash": anchor_receipt.tx_hash,
                    "mode": anchor_receipt.mode,
                    "chain_id": anchor_receipt.chain_id,
                    "metadata": anchor_receipt.metadata,
                }
            if security_envelope:
                response_payload["_qso_security"] = security_envelope

            if response_filter is not None:
                try:
                    response_payload["_qso_quantum_filter"] = {
                        "lower_bound": response_filter.filter_payload(
                            response_payload,
                            conversation_id=str(request.get("conversation_id", "main")),
                            phase="lower_bound",
                        ),
                        "upper_bound": response_filter.filter_payload(
                            response_payload,
                            conversation_id=str(request.get("conversation_id", "main")),
                            phase="upper_bound",
                        ),
                    }
                except Exception as exc:
                    if require_response_filter:
                        await ws.send(json.dumps({"error": "quantum_filter_failed", "detail": str(exc)}))
                        continue
                    response_payload["_qso_quantum_filter"] = {
                        "status": "degraded",
                        "detail": str(exc),
                    }
            elif require_response_filter:
                await ws.send(json.dumps({"error": "quantum_filter_required"}))
                continue

            await ws.send(json.dumps(response_payload, sort_keys=True))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qso-chat-ws", description="Read-only websocket tail viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--tls-cert", default=os.getenv("QSO_CHAT_WS_TLS_CERT", "").strip() or None)
    parser.add_argument("--tls-key", default=os.getenv("QSO_CHAT_WS_TLS_KEY", "").strip() or None)
    parser.add_argument("--auth-token", default=os.getenv("QSO_CHAT_WS_AUTH_TOKEN", "").strip() or None)
    parser.add_argument("--pq-seed-hex", default=os.getenv("QSO_CHAT_WS_PQ_SEED_HEX", "").strip() or None)
    parser.add_argument("--pq-private-key", default=os.getenv("QSO_CHAT_WS_PQ_PRIVATE_KEY", "").strip() or None)
    parser.add_argument("--pq-signature-algo", default=os.getenv("QSO_CHAT_WS_PQ_SIGNATURE_ALGO", "ML-DSA-65"))
    parser.add_argument("--pq-kem-algo", default=os.getenv("QSO_CHAT_WS_PQ_KEM_ALGO", "ML-KEM-768"))
    parser.add_argument(
        "--pq-crypto-profile-id",
        default=os.getenv("QSO_CHAT_WS_PQ_CRYPTO_PROFILE_ID", "X25519+ML-KEM-768/ML-DSA-65"),
    )
    parser.add_argument(
        "--anchor-contract-address",
        default=os.getenv("QSO_CHAT_WS_ANCHOR_CONTRACT_ADDRESS", "").strip() or None,
    )
    parser.add_argument("--anchor-rpc-url", default=os.getenv("QSO_CHAT_WS_ANCHOR_RPC_URL", "").strip() or None)
    parser.add_argument(
        "--anchor-private-key",
        default=os.getenv("QSO_CHAT_WS_ANCHOR_PRIVATE_KEY", "").strip() or None,
    )
    parser.add_argument(
        "--anchor-live",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_ANCHOR_LIVE", False),
        help="When anchoring is enabled, submit transactions instead of deterministic signed-hash mode.",
    )
    parser.add_argument(
        "--require-tls",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_REQUIRE_TLS", False),
        help="Fail closed unless TLS is configured.",
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_REQUIRE_AUTH", False),
        help="Fail closed unless auth token is configured.",
    )
    parser.add_argument(
        "--require-quantum-envelope",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE", False),
        help="Fail closed unless PQ signer is configured.",
    )
    parser.add_argument(
        "--require-contract-anchor",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR", False),
        help="Fail closed unless contract anchoring is configured.",
    )
    parser.add_argument(
        "--itensor-filter",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_ITENSOR_FILTER", False),
        help="Attach ITensor-backed quantum diagnostics to each websocket tail response.",
    )
    parser.add_argument(
        "--require-itensor-filter",
        action="store_true",
        default=_env_flag("QSO_CHAT_WS_REQUIRE_ITENSOR_FILTER", False),
        help="Fail closed unless the websocket response filter can run.",
    )
    parser.add_argument(
        "--itensor-filter-uri-prefix",
        default=os.getenv("QSO_CHAT_WS_ITENSOR_FILTER_URI_PREFIX", "qso://quantum.state/filter/ws"),
    )
    parser.add_argument(
        "--itensor-filter-max-qubits",
        type=int,
        default=int(os.getenv("QSO_CHAT_WS_ITENSOR_FILTER_MAX_QUBITS", "8")),
    )
    return parser


def _build_signer(args: argparse.Namespace) -> QuantumSocketSigner | None:
    private_key = str(args.pq_private_key or "").strip()
    if private_key:
        return QuantumSocketSigner(
            private_key_hex=private_key,
            signature_algo=str(args.pq_signature_algo),
            kem_algo=str(args.pq_kem_algo),
            crypto_profile_id=str(args.pq_crypto_profile_id),
        )

    seed_hex = str(args.pq_seed_hex or "").strip()
    if not seed_hex:
        return None
    return QuantumSocketSigner.from_seed_hex(
        seed_hex,
        signature_algo=str(args.pq_signature_algo),
        kem_algo=str(args.pq_kem_algo),
        crypto_profile_id=str(args.pq_crypto_profile_id),
    )


def _build_anchor_ledger(args: argparse.Namespace) -> SolidityAnchorSocketLedger | None:
    contract_address = str(args.anchor_contract_address or "").strip()
    if not contract_address:
        return None
    return SolidityAnchorSocketLedger(
        contract_address=contract_address,
        rpc_url=(None if args.anchor_rpc_url is None else str(args.anchor_rpc_url)),
        private_key=(None if args.anchor_private_key is None else str(args.anchor_private_key)),
        deterministic_mode=not bool(args.anchor_live),
    )


def _validate_requirements(
    args: argparse.Namespace,
    *,
    signer: QuantumSocketSigner | None,
    anchor_ledger: SolidityAnchorSocketLedger | None,
) -> None:
    tls_configured = bool(args.tls_cert and args.tls_key)
    auth_configured = bool(args.auth_token and str(args.auth_token).strip())
    if bool(args.require_tls) and not tls_configured:
        raise SystemExit("requirement failed: TLS is required (--require-tls)")
    if bool(args.require_auth) and not auth_configured:
        raise SystemExit("requirement failed: auth token is required (--require-auth)")
    if bool(args.require_quantum_envelope) and signer is None:
        raise SystemExit("requirement failed: quantum envelope signer is required (--require-quantum-envelope)")
    if bool(args.require_contract_anchor) and anchor_ledger is None:
        raise SystemExit("requirement failed: contract anchor is required (--require-contract-anchor)")


async def _main(
    host: str,
    port: int,
    *,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    auth_token: str | None = None,
    signer: QuantumSocketSigner | None = None,
    anchor_ledger: SolidityAnchorSocketLedger | None = None,
    response_filter: QuantumResponseFilter | None = None,
    require_response_filter: bool = False,
) -> None:
    tls_context = build_tls_context(tls_cert, tls_key)

    async def _serve_bound(ws: Any) -> None:
        await _serve(
            ws,
            auth_token=auth_token,
            signer=signer,
            anchor_ledger=anchor_ledger,
            tls_enabled=tls_context is not None,
            response_filter=response_filter,
            require_response_filter=require_response_filter,
        )

    async with websockets.serve(_serve_bound, host, port, ssl=tls_context):
        await asyncio.Future()


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    signer = _build_signer(args)
    anchor_ledger = _build_anchor_ledger(args)
    _validate_requirements(args, signer=signer, anchor_ledger=anchor_ledger)
    response_filter = None
    if bool(args.itensor_filter) or bool(args.require_itensor_filter):
        response_filter = QuantumResponseFilter(
            backend="itensor",
            uri_prefix=str(args.itensor_filter_uri_prefix),
            max_qubits=int(args.itensor_filter_max_qubits),
        )
    try:
        asyncio.run(
            _main(
                args.host,
                args.port,
                tls_cert=args.tls_cert,
                tls_key=args.tls_key,
                auth_token=(str(args.auth_token).strip() if args.auth_token else None),
                signer=signer,
                anchor_ledger=anchor_ledger,
                response_filter=response_filter,
                require_response_filter=bool(args.require_itensor_filter),
            )
        )
    except KeyboardInterrupt:
        return None


if __name__ == "__main__":
    main()
