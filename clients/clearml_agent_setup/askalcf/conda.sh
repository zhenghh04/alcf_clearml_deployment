#!/bin/bash
# Activate the dedicated ClearML venv on the AskALCF VM.
#
# The AskALCF VM ships Ubuntu 22.04's stock /usr/bin/python3 (3.10) with
# NO system pip. We bootstrap a venv at ~/clearml/venv during onboarding
# and install clearml-agent into it. Keeping this venv separate from the
# RAG/MCP service env in /home/huihuo.zheng/askalcf/conda/ avoids
# perturbing the production-data Globus daemon.
#
# Bootstrap (one-time, on the VM):
#   python3 -m venv ~/clearml/venv
#   ~/clearml/venv/bin/python -m pip install -U pip
#   ~/clearml/venv/bin/python -m pip install --extra-index-url \
#       https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple \
#       clearml-agent==2.0.7rc5

source "${HOME}/clearml/venv/bin/activate"
