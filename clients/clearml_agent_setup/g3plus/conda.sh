#!/bin/bash
# Activate the dedicated ClearML venv on g3plus.
#
# g3plus has /opt/miniconda3 system-wide, but we use an isolated venv
# at ~/clearml/venv so the agent environment is reproducible and doesn't
# perturb the system Python or any conda envs.
#
# Bootstrap (one-time, on g3plus):
#   python3 -m venv ~/clearml/venv
#   ~/clearml/venv/bin/python -m pip install -U pip
#   source ~/clearml/alcf_clearml_deployment/.env
#   ~/clearml/venv/bin/python -m pip install \
#       --extra-index-url "https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple" \
#       clearml-agent==2.0.7rc5

source "${HOME}/clearml/venv/bin/activate"
