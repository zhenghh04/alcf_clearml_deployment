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

## Repo checkout cache and filesystem issues
If the agent fails to checkout the repo (e.g., `not a git repository` or missing files under `_execute_.../task_repository`), point the cache to a local writable filesystem and clear stale caches:

```bash
export CLEARML_CACHE_DIR=/tmp/clearml
export CLEARML_AGENT_VCS_CACHE_DIR=/tmp/clearml/vcs-cache
rm -rf /home/$USER/.clearml/vcs-cache/alcf_clearml_evaluation.git.*
rm -rf /lus/eagle/projects/*/$USER/clearml/.clearml/_execute_*
```

Then restart the agent.

## Create and listen to a queue
ClearML queues are created implicitly when a task is enqueued to a new queue name. Agents can only attach to existing queues.

Start an agent listening to `my-queue`:
```bash
CLIENT=sirius QUEUE=my-queue bash clients/launch_clearml_agent.sh
```

Enqueue a task to `my-queue`:
```python
Task.enqueue(created_task, queue_name="my-queue")
```

## Templates
Queue templates are in:
- `clients/crux/pbs.template`
- `clients/polaris/pbs.template`
- `clients/sirius/pbs.template`

Adjust walltime, nodes, account, and other scheduler directives as needed for your project.

## Perlmutter (draft)
An initial Perlmutter client bootstrap is available under:
- `clients/perlmutter/README.md`
- `clients/perlmutter/setup_env.sh`

Create the environment with:
```bash
bash clients/perlmutter/setup_env.sh
```
