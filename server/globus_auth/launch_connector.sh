#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONNECTOR_DIR="${ROOT_DIR}/server/globus_auth"
ENV_FILE="${CONNECTOR_DIR}/.env"
PORT="${PORT:-8503}"
HOST="${HOST:-0.0.0.0}"
INSTALL_DEPS="${INSTALL_DEPS:-0}"
DETACH="${DETACH:-0}"
LOG_FILE="${LOG_FILE:-${CONNECTOR_DIR}/connector.log}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found. Copy .env.example and fill values first." >&2
  exit 1
fi

if [[ "${INSTALL_DEPS}" == "1" ]]; then
  python -m pip install -r "${CONNECTOR_DIR}/requirements.txt"
fi

# Stop any existing connector process so relaunch is idempotent.
pkill -f "uvicorn server\\.globus_auth\\.main:app" >/dev/null 2>&1 || true

set -a
source "${ENV_FILE}"
set +a

if [[ "${DETACH}" == "1" ]]; then
  nohup uvicorn server.globus_auth.main:app --host "${HOST}" --port "${PORT}" > "${LOG_FILE}" 2>&1 &
  echo "Globus connector started in background on ${HOST}:${PORT} (pid=$!)."
  echo "Logs: ${LOG_FILE}"
else
  exec uvicorn server.globus_auth.main:app --host "${HOST}" --port "${PORT}"
fi
