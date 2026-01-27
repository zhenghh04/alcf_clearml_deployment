# ClearML client setup (agents)

This folder contains scripts and templates for installing and launching ClearML agents on ALCF systems.

## Install ClearML agents
Use the provided install script:
```bash
bash clients/install_clearml.sh
```

This installs `clearml-agent-slurm` and `clearml-agent`. Update the package versions inside `clients/install_clearml.sh` if needed.

## Configure ClearML
Place your ClearML config at one of:
- `~/clearml.conf`
- `~/.clearml.conf`

Example configs live under `clients/*/clearml.conf`. Copy the one matching your system and edit the server URLs and credentials:
```bash
cp clients/sirius/clearml.conf ~/.clearml.conf
```

## Launch agents
Use the launcher script, selecting the system via `CLIENT` and (optionally) `QUEUE`:
```bash
CLIENT=sirius QUEUE=sirius bash clients/launch_clearml_agent.sh
```

This starts:
- a PBS-backed agent using `clients/<CLIENT>/pbs.template`
- a login-node agent queue named `<QUEUE>-login`

## Templates
Queue templates are in:
- `clients/crux/pbs.template`
- `clients/polaris/pbs.template`
- `clients/sirius/pbs.template`

Adjust walltime, nodes, account, and other scheduler directives as needed for your project.
