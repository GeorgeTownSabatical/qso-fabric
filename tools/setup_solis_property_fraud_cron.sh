#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="${ROOT_DIR}/tools/run_solis_property_fraud_scheduled.sh"
MARKER="qso_solis_property_fraud_run"
SCHEDULE="${SOLIS_PROPERTY_FRAUD_CRON_SCHEDULE:-17 */6 * * *}"

if [[ ! -x "${RUNNER}" ]]; then
  echo "Runner script is missing or not executable: ${RUNNER}" >&2
  exit 1
fi

ENTRY="${SCHEDULE} /bin/zsh -lc '${RUNNER}' # ${MARKER}"
TMP_CRON="$(mktemp)"
trap 'rm -f "${TMP_CRON}"' EXIT

if crontab -l > "${TMP_CRON}" 2>/dev/null; then
  :
else
  : > "${TMP_CRON}"
fi

grep -v "# ${MARKER}\$" "${TMP_CRON}" > "${TMP_CRON}.new" || true
mv "${TMP_CRON}.new" "${TMP_CRON}"
printf '%s\n' "${ENTRY}" >> "${TMP_CRON}"

crontab "${TMP_CRON}"

echo "Installed cron entry:"
echo "${ENTRY}"
