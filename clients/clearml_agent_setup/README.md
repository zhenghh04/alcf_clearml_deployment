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

## Agent environment settings in Configuration Vault
If you want the Configuration Vault to affect how the ClearML agent starts task environments, put the settings under the `agent` section and then restart the agent so it reloads the vault.

Example vault entry for a user-managed venv-based agent:
```hocon
agent {
  python_binary: "/path/to/venv/bin/python"
  extra_docker_arguments: [
    "-e", "CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1",
    "-e", "CLEARML_AGENT_SKIP_PIP_VENV_INSTALL=/path/to/venv/bin/python"
  ]
}
```

Suggested workflow in the ClearML Web UI:
1. Open **Settings** -> **Configuration Vault**.
2. Create or edit the vault entry that applies to the user/group/agent host that will run the task.
3. Paste the `agent { ... }` block above and replace `/path/to/venv/bin/python` with the Python executable available on that worker.
4. Save the vault entry and restart the affected ClearML agent process.

Important limitations:
- This works best for queues backed by agents you control.
- If the task runs on a shared Docker-based `services` queue, the Python path must exist inside that worker environment or the task will still fail.
- Vault config can override agent config fields, but it does not automatically convert an unrelated shared Docker worker into your own host venv worker.
- For task-specific runtime variables, use task parameters like `task.set_parameters_as_dict({"env:KEY": "value"})` instead of the vault.

## GitHub credentials in Configuration Vault
If your ClearML tasks clone a private GitHub repository over HTTPS, store the GitHub credentials in the ClearML Configuration Vault so agents can reuse them without keeping tokens in `~/.clearml.conf`.

Recommended values:
- Use a GitHub Personal Access Token (PAT) with read access to the target repository.
- Use an HTTPS repository URL in the task, for example `https://github.com/<org>/<repo>.git`.
- Store the credentials under the `agent` section so ClearML Agent can inject them during `git clone`.

Create a new GitHub PAT:
1. Open GitHub **Settings** -> **Developer settings** -> **Personal access tokens** -> **Fine-grained tokens**.
2. Click **Generate new token**.
3. Set a descriptive token name such as `clearml-agent-clone`.
4. Pick a practical expiration time.
5. Set the resource owner to the user or organization that owns the repository.
6. Choose **Only select repositories** and select the repository the agent must clone.
7. Under repository permissions, grant:
   - **Contents**: **Read-only**
   - **Metadata**: **Read-only**
8. Generate the token and copy it immediately.

If fine-grained tokens are blocked in your environment, a classic PAT with `repo` scope also works, but fine-grained is preferred.

Add a vault configuration similar to:
```hocon
agent {
  git_user: "<GITHUB_USERNAME>"
  git_pass: "<GITHUB_PAT>"
}
```

Suggested workflow in the ClearML Web UI:
1. Open **Settings** -> **Configuration Vault**.
2. Create or edit the vault entry that applies to the user/group/agent host that will run the task.
3. Paste the `agent.git_user` and `agent.git_pass` values above.
4. Save the vault entry and restart the affected ClearML agent process so it reloads the vault.

Validation:
- Start or restart the agent and check the startup log for a line similar to `Loaded group vault for user ...`.
- Submit a task that points to a private HTTPS GitHub repository.
- If cloning still fails, confirm the PAT is still valid and has repository read permission.
- If the repository belongs to an organization with SSO or approval requirements, authorize or approve the token there as well.
- If the repository contains private submodules, the PAT must also have read access to those repositories because ClearML clones with `--recursive`.

Notes:
- `agent.git_user` / `agent.git_pass` are intended for HTTPS cloning. If your task uses `git@github.com:...`, configure SSH keys on the agent instead.
- For one-off local testing, you can also export `CLEARML_AGENT_GIT_USER` and `CLEARML_AGENT_GIT_PASS`, but the configuration vault is the cleaner shared setup.
- If a PAT was stored in plaintext in an `.env` file, shell history, or logs, rotate it after moving the secret into the vault.

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
