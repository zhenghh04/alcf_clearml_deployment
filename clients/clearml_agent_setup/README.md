# ClearML Agent Setup

This folder contains scripts and templates for installing and launching ClearML agents on ALCF systems.

## Install ClearML agents
```bash
bash clients/clearml_agent_setup/install_clearml.sh
```

## Configure ClearML
Place your ClearML config at one of:
- `~/clearml.conf`
- `~/.clearml.conf`

Example:
```bash
cp clients/clearml_agent_setup/sirius/clearml.conf ~/.clearml.conf
```

## Queue prerequisite
Before launching agents, create the target queues in the ClearML Server dashboard
(for example `sirius`, `sirius-login`, `sirius-services`, or your custom names).

After queues exist, start agents and point them to the same queue names so they can
pick up tasks from those queues.

## Launch agents
```bash
CLIENT=sirius QUEUE=sirius bash clients/clearml_agent_setup/launch_clearml_agent.sh
```

This starts:
- a scheduler-backed agent using `clients/clearml_agent_setup/<CLIENT>/<scheduler>.template`
- a login-node agent queue named `<QUEUE>-login`
- a services queue named `<QUEUE>-services`

Scheduler is auto-detected from `clients/clearml_agent_setup/<CLIENT>/system.conf` and can be overridden with `SCHEDULER=pbs|slurm`.

## Queue templates
- `clients/clearml_agent_setup/crux/pbs.template`
- `clients/clearml_agent_setup/polaris/pbs.template`
- `clients/clearml_agent_setup/sirius/pbs.template`
- `clients/clearml_agent_setup/perlmutter/slurm.template`

## Perlmutter notes
- `clients/clearml_agent_setup/perlmutter/README.md`
- `clients/clearml_agent_setup/perlmutter/setup_env.sh`
