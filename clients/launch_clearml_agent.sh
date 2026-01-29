#!/bin/bash
export CLIENT=${CLIENT:-"sirius"}
export OPENBLAS_NUM_THREADS=1
echo "Starting ClearML agent on ALCF with client: ${CLIENT}"
source ${CLIENT}/conda.sh
export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL="$(which python3)"
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export K8S_GLUE_POD_AGENT_INSTALL_ARGS="==2.0.7rc5"

[[ -e ../.env ]] && echo "Setting environment variables in ../.env"

# Kill existing agent
pkill clearml-agent-slurm
pkill clearml-agent

nohup clearml-agent-slurm --template-files ${CLIENT}/pbs.template --queue ${QUEUE:-$CLIENT} --use-pbs & 
nohup clearml-agent daemon --detached --queue ${QUEUE:-$CLIENT}-login &
