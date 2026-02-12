#!/usr/bin/env bash
set -euo pipefail

module load python/3.13

python -m venv $HOME/clearml/alcf_clearml_evaluation/clients/perlmutter/envs/clearml

source $HOME/clearml/alcf_clearml_evaluation/clients/perlmutter/envs/clearml/bin/activate
sh ../install_clearml.sh

