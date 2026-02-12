#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PERLMUTTER_CLEARML_VENV:-${SCRIPT_DIR}/venvs/clearml}"

if command -v module >/dev/null 2>&1; then
  module load python >/dev/null 2>&1 || true
fi

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
  echo "ERROR: Perlmutter ClearML env not found at ${VENV_DIR}" >&2
  echo "Run clients/perlmutter/setup_env.sh first." >&2
  return 1 2>/dev/null || exit 1
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"
