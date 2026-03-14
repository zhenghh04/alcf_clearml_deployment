#!/bin/bash -x
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENTS_ENV="${SCRIPT_DIR}/../.env"
REPO_ENV="${SCRIPT_DIR}/../../.env"

if [[ -e "${CLIENTS_ENV}" ]]; then
  source "${CLIENTS_ENV}"
elif [[ -e "${REPO_ENV}" ]]; then
  source "${REPO_ENV}"
else
  echo "please define CLEARML_PIP_PACKAGE_USER and CLEARML_PIP_PACKAGE_PASS in clients/.env or ./.env"
  echo "Your credentials for --extra-index-url are available in the WebApp under Help > ClearML Python Package setup > Install."
fi

python3 -m pip install -U --extra-index-url https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple \
    clearml-agent-slurm==0.10.1 \
    clearml-agent==2.0.7rc5
