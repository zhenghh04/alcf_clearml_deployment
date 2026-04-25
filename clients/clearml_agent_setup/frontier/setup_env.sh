#!/usr/bin/env bash
# Install ClearML agent environment on Frontier.
# Run once from a Frontier login node:
#   bash clients/clearml_agent_setup/frontier/setup_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${FRONTIER_CLEARML_VENV:-$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/frontier/envs/clearml}"

# Frontier provides miniforge via module; use it to get a clean Python.
module load miniforge3/23.11.0-0 2>/dev/null || module load python 2>/dev/null || true

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

cd "${SCRIPT_DIR}/.."
bash install_clearml.sh

echo "Environment created at: ${VENV_DIR}"
echo "Activate with: source ${VENV_DIR}/bin/activate"
