#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/.codex/state/mesh_integrity"
LOG_FILE="${STATE_DIR}/cron.log"

mkdir -p "${STATE_DIR}"

ENV_FILES_RAW="${QSO_MESH_ENV_FILES:-${ROOT_DIR}/.codex/state/mesh.env}"
IFS=':' read -r -a ENV_FILES <<< "${ENV_FILES_RAW}"

CMD=("${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/tools/mesh_integrity_check.py")
for env_file in "${ENV_FILES[@]}"; do
  if [[ -n "${env_file}" ]]; then
    CMD+=("--env-file" "${env_file}")
  fi
done

{
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] start mesh integrity check"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] env_files=${ENV_FILES_RAW}"
  set +e
  "${CMD[@]}"
  rc=$?
  set -e
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] exit_code=${rc}"
  exit "${rc}"
} >> "${LOG_FILE}" 2>&1
