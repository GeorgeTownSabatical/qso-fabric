#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.codex/state/qso_chat_ws.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Run tools/setup_qso_chat_ws_hardened.sh first." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

if [[ -n "${QSO_CHAT_WS_OQS_INSTALL_PATH:-}" ]]; then
  export OQS_INSTALL_PATH="${QSO_CHAT_WS_OQS_INSTALL_PATH}"
fi

cmd=(
  "${ROOT_DIR}/.venv/bin/python"
  -m
  tools.qso_chat_ws
  --host "${QSO_CHAT_WS_HOST:-0.0.0.0}"
  --port "${QSO_CHAT_WS_PORT:-9444}"
  --tls-cert "${QSO_CHAT_WS_TLS_CERT}"
  --tls-key "${QSO_CHAT_WS_TLS_KEY}"
  --auth-token "${QSO_CHAT_WS_AUTH_TOKEN}"
  --pq-seed-hex "${QSO_CHAT_WS_PQ_SEED_HEX}"
  --anchor-contract-address "${QSO_CHAT_WS_ANCHOR_CONTRACT_ADDRESS}"
)

if [[ "${QSO_CHAT_WS_REQUIRE_TLS:-0}" == "1" ]]; then
  cmd+=(--require-tls)
fi
if [[ "${QSO_CHAT_WS_REQUIRE_AUTH:-0}" == "1" ]]; then
  cmd+=(--require-auth)
fi
if [[ "${QSO_CHAT_WS_REQUIRE_QUANTUM_ENVELOPE:-0}" == "1" ]]; then
  cmd+=(--require-quantum-envelope)
fi
if [[ "${QSO_CHAT_WS_REQUIRE_CONTRACT_ANCHOR:-0}" == "1" ]]; then
  cmd+=(--require-contract-anchor)
fi

if [[ "${QSO_CHAT_WS_ANCHOR_LIVE:-0}" == "1" ]]; then
  if [[ -z "${QSO_CHAT_WS_ANCHOR_RPC_URL:-}" || -z "${QSO_CHAT_WS_ANCHOR_PRIVATE_KEY:-}" ]]; then
    echo "QSO_CHAT_WS_ANCHOR_LIVE=1 requires QSO_CHAT_WS_ANCHOR_RPC_URL and QSO_CHAT_WS_ANCHOR_PRIVATE_KEY." >&2
    exit 2
  fi
  cmd+=(--anchor-rpc-url "${QSO_CHAT_WS_ANCHOR_RPC_URL}" --anchor-private-key "${QSO_CHAT_WS_ANCHOR_PRIVATE_KEY}" --anchor-live)
fi

exec "${cmd[@]}"
