#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load python/3.13
python -m venv $HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/perlmutter/envs/clearml
source $HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/perlmutter/envs/clearml/bin/activate
cd "${SCRIPT_DIR}/.."
bash install_clearml.sh
