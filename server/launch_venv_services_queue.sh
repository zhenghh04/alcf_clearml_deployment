#!/bin/bash
export OPENBLAS_NUM_THREADS=1
echo "Starting ClearML agent on ALCF with client: ${CLIENT}"
export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL="$(which python3)"
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export K8S_GLUE_POD_AGENT_INSTALL_ARGS="==2.0.7rc5"

clearml-agent daemon --services --queue ${QUEUE:-"venv-services-queue"} --detached
