#!/usr/bin/env bash
set -euo pipefail
module load python/3.13
VENV_DIR=$HOME/clearml/alcf_clearml_evaluation/clients/perlmutter/envs/clearml/
source "${VENV_DIR}/bin/activate"
