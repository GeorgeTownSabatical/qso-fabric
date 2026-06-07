#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/.codex/state"
RUN_DIR="${STATE_DIR}/solis_property_fraud"
HISTORY_DIR="${RUN_DIR}/history"
LOG_FILE="${RUN_DIR}/cron.log"
MANIFEST_FILE="${RUN_DIR}/last_run_manifest.json"
RUN_TS="$(date -u +"%Y%m%dT%H%M%SZ")"

mkdir -p "${RUN_DIR}" "${HISTORY_DIR}"

{
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] start solis-property-fraud scheduled run"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] root=${ROOT_DIR}"

  "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/tools/dev_automation.py" property-fraud

  SCORES_FILE="${STATE_DIR}/solis_property_fraud_scores.jsonl"
  SUMMARY_FILE="${STATE_DIR}/solis_property_fraud_summary.json"

  if [[ -f "${SCORES_FILE}" ]]; then
    SCORES_VERSIONED="${HISTORY_DIR}/scores_${RUN_TS}.jsonl"
    cp "${SCORES_FILE}" "${SCORES_VERSIONED}"
    SCORES_HASH="$(shasum -a 256 "${SCORES_VERSIONED}" | awk '{print $1}')"
  else
    SCORES_VERSIONED=""
    SCORES_HASH=""
  fi

  if [[ -f "${SUMMARY_FILE}" ]]; then
    SUMMARY_VERSIONED="${HISTORY_DIR}/summary_${RUN_TS}.json"
    cp "${SUMMARY_FILE}" "${SUMMARY_VERSIONED}"
    SUMMARY_HASH="$(shasum -a 256 "${SUMMARY_VERSIONED}" | awk '{print $1}')"
  else
    SUMMARY_VERSIONED=""
    SUMMARY_HASH=""
  fi

  cat > "${MANIFEST_FILE}" <<EOF
{
  "run_ts": "${RUN_TS}",
  "root_dir": "${ROOT_DIR}",
  "scores_file": "${SCORES_FILE}",
  "scores_versioned_file": "${SCORES_VERSIONED}",
  "scores_hash_sha256": "${SCORES_HASH}",
  "summary_file": "${SUMMARY_FILE}",
  "summary_versioned_file": "${SUMMARY_VERSIONED}",
  "summary_hash_sha256": "${SUMMARY_HASH}"
}
EOF

  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] completed solis-property-fraud scheduled run"
} >> "${LOG_FILE}" 2>&1
