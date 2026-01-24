#!/bin/bash +x
pip install -U --extra-index-url https://USERNAME:PASSWORD@packages.allegro.ai/repository/clearml_agent_slurm/simple \
    clearml-agent-slurm==0.10.1 \
    clearml-agent==2.0.7rc5

