#!/bin/bash
export CLIENT=${CLIENT:-$HOSTNAME}
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
echo "Starting ClearML agent on ALCF with client: ${CLIENT}"
export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL="$(which python3)"
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export K8S_GLUE_POD_AGENT_INSTALL_ARGS="==2.0.7rc5"

echo "I am assuming that this is on your laptop or a system that is not a login node of a cluster."
pkill clearml-agent
nohup clearml-agent daemon --detached --queue ${QUEUE:-$CLIENT} &
