#!/usr/bin/env bash
# Source this file to activate the ClearML environment on Frontier.
module load miniforge3/23.11.0-0 2>/dev/null || module load python 2>/dev/null || true
VENV_DIR="${FRONTIER_CLEARML_VENV:-$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/frontier/envs/clearml}"
source "${VENV_DIR}/bin/activate"
