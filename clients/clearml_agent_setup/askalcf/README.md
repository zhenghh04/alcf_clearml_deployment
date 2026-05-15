# AskALCF client

Services-mode ClearML agent on the AskALCF RAG VM
(`askalcf.alcf.anl.gov`, ProxyJump `login-gce`).

## Why services-mode?

Plain Ubuntu VM, no PBS/Slurm. One `clearml-agent daemon --services-mode`
on the VM handles all `askalcf-services` queue work. Production web/MCP
services for AskALCF run separately on the ALCF Hermes K8s cluster
(namespace `askalcf`); this agent is for lightweight indexing / RAG
batch tasks driven from the agentic-workflows project.

## Bootstrap (one-time)

The AskALCF VM has no system pip, so we use a dedicated venv. From the
VM (after `git clone alcf_clearml_deployment` and `.env` is in place):

```bash
mkdir -p ~/clearml
python3 -m venv ~/clearml/venv
~/clearml/venv/bin/python -m pip install -U pip

# Reads CLEARML_PIP_PACKAGE_USER / CLEARML_PIP_PACKAGE_PASS from
# ~/clearml/alcf_clearml_deployment/.env
source ~/clearml/alcf_clearml_deployment/.env
~/clearml/venv/bin/python -m pip install \
    --extra-index-url "https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple" \
    clearml-agent==2.0.7rc5
```

Then drop a `~/.clearml.conf` (copy from another client like
`clients/clearml_agent_setup/sirius/clearml.conf` and edit credentials).

## Launch

```bash
cd ~/clearml/alcf_clearml_deployment/clients/clearml_agent_setup
CLIENT=askalcf bash launch_clearml_agent.sh
```

`launch_clearml_agent.sh` reads `askalcf/system.conf` (`SCHEDULER=services`),
sources `askalcf/conda.sh` (activates the venv), and starts a single
`--services-mode` daemon on the `askalcf-services` queue. No login
daemon, no PBS template.

## Pre-flight: queues must exist on the ClearML server

Before launching, create the `askalcf-services` queue in the ClearML
WebUI (Settings -> Queues -> +Queue). The agent fails to start if the
queue does not exist.
