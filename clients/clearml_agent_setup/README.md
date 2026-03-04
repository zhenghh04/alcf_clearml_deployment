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

Update the copied `clearml.conf` with your site-specific values:
- `api.api_server`, `api.web_server`, `api.files_server`: set to your ClearML server URLs.
- `api.credentials.access_key`, `api.credentials.secret_key`: set your user API credentials.
- `agent.python_binary`: set to the Python interpreter used by your ClearML agent environment.
- Scheduler-specific values under `agent.slurm` (or PBS mode), such as monitor command/user, should match your system account and scheduler commands.
- If you are not using container mode and want jobs to run in a custom Python environment, setting `agent.python_binary` correctly is essential.

Where to get the required information:
- Server URLs: from your ClearML server deployment settings (same endpoints configured in server `constants.env`).
- API credentials: ClearML Web UI -> user profile -> **Settings** -> **Workspace API Credentials**.
- Agent Python path: run `which python` inside the environment you use to launch the agent.
- Scheduler/account values: from your HPC site documentation and your allocated project/account info.

Minimal example (`api` section):
```hocon
api {
  api_server: https://<your-clearml-host>/api/
  web_server: https://<your-clearml-host>/
  files_server: https://<your-clearml-host>/files/
  credentials {"access_key": "<ACCESS_KEY>", "secret_key": "<SECRET_KEY>"}
}
```

Quick check after editing:
```bash
clearml-agent daemon --help
```
If this command runs without configuration errors, the local config is readable by ClearML tools.

## Queue prerequisite
Before launching agents, create the target queues in the ClearML Server dashboard
(for example `sirius`, `sirius-login`, `sirius-services`, or your custom names).

![ClearML queue creation page showing pre-created queues](queue-prerequisite-queues-page.png)

Example view from the ClearML dashboard where queues are created before starting agents.

After queues exist, start agents and point them to the same queue names so they can
pick up tasks from those queues.

## Launch agents
```bash
CLIENT=sirius bash clients/clearml_agent_setup/launch_clearml_agent.sh
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

Use the scheduler template that matches your system:
- `pbs.template` for PBS/Torque-style schedulers (for example Crux, Polaris, Sirius).
- `slurm.template` for Slurm schedulers (for example Perlmutter).
- Each user can configure their own PBS/Slurm connector on the login node by using a user-specific `clearml.conf`, scheduler template, and account/QoS settings.
- After adopting these templates, you can control scheduler resources from your task code using `task.set_user_properties(...)` (for example number of nodes, account, walltime, and related queue/scheduler fields).

Quoted examples:

`pbs.template` (key lines):
```bash
#PBS -N clearml_task_${CLEARML_TASK.id}
#PBS -l select=${CLEARML_TASK.hyperparams.properties.num_nodes.value:1}:ncpus=1
#PBS -l walltime=1:00:00
...
${CLEARML_PRE_SETUP}
${CLEARML_AGENT_EXECUTE}
${CLEARML_POST_SETUP}
```

`slurm.template` (key lines):
```bash
#SBATCH --job-name=clearml_${CLEARML_TASK.id}
#SBATCH --time=${CLEARML_TASK.hyperparams.properties.walltime.value:01:00:00}
#SBATCH --nodes=${CLEARML_TASK.hyperparams.properties.num_nodes.value:1}
...
${CLEARML_PRE_SETUP}
${CLEARML_AGENT_EXECUTE}
${CLEARML_POST_SETUP}
```

## Perlmutter notes
- `clients/clearml_agent_setup/perlmutter/README.md`
- `clients/clearml_agent_setup/perlmutter/setup_env.sh`
