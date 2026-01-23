#!/bin/bash
export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL="/home/hzheng/clearml/miniconda3/bin/python"
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export K8S_GLUE_POD_AGENT_INSTALL_ARGS="==2.0.7rc5"
export https_proxy=http://proxy.alcf.anl.gov:3128
export http_proxy=http://proxy.alcf.anl.gov:3128
export PATH=/home/hzheng/clearml/miniconda3/bin/:$PATH
clearml-agent-slurm --template-files ./pbs.template --queue default --use-pbs
