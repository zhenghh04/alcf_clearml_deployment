#!/bin/bash -x

[[ -e ../.env ]] && source ../.env || echo "please define CLEARML_PIP_PACKAGE_USER and CLEARML_PIP_PACKAGE_PASS in ../.env\n Your credentials for --extra-index-url are available in the WebApp under the Help menu Help menu > ClearML Python Package setup > Install step."
pip install -U --extra-index-url https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple \
    clearml-agent-slurm==0.10.1 \
    clearml-agent==2.0.7rc5

