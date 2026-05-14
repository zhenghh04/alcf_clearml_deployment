# Frontier ClearML Client Setup

OLCF Frontier — AMD MI250X exascale system, Slurm scheduler, project CSC708.

## 1. SSH to Frontier

```bash
ssh hzheng@frontier.olcf.ornl.gov
```

## 2. Clone the deployment repo

```bash
cd $HOME
git clone <repo-url> clearml/alcf_clearml_deployment
cd clearml/alcf_clearml_deployment
```

## 3. Set credentials in clients/.env

```bash
cat > clients/.env <<EOF
CLEARML_PIP_PACKAGE_USER=<from ClearML WebApp Help>
CLEARML_PIP_PACKAGE_PASS=<from ClearML WebApp Help>
EOF
```

## 4. Install the ClearML environment

```bash
bash clients/clearml_agent_setup/frontier/setup_env.sh
```

## 5. Configure clearml.conf

Copy the template and fill in your API credentials:

```bash
cp clients/clearml_agent_setup/frontier/clearml.conf ~/.clearml.conf
# Edit ~/.clearml.conf: set access_key and secret_key from
# https://amscclearml.alcf.anl.gov/app/profile
```

## 6. Start agents

```bash
CLIENT=frontier bash clients/clearml_agent_setup/launch_clearml_agent.sh
```

This starts three agents:
| Agent | Queue | Purpose |
|-------|-------|---------|
| `clearml-agent-slurm` | `frontier` | Compute jobs via sbatch |
| `clearml-agent daemon` | `frontier-login` | One-shot tasks on login node |
| `clearml-agent daemon --services-mode` | `frontier-services` | Long-running services |

## 7. Make agents survive logout and reboots

By default `systemctl --user` services are torn down when your last login session ends, so the agents would only run while you are SSH'd in. To keep them running across logouts and login-node reboots:

**Step 1 — enable lingering** (one-time, persists forever):

```bash
loginctl enable-linger $USER
loginctl show-user $USER | grep Linger    # should print: Linger=yes
```

OLCF allows users to enable linger themselves — no `sudo` and no ticket required.

**Step 2 — install and enable the user service**:

```bash
CLIENT=frontier bash clients/clearml_agent_setup/launch_clearml_agent.sh --install-service
```

This writes `~/.config/systemd/user/clearml-agent-frontier.service` (with `[Install] WantedBy=default.target`) and runs `systemctl --user enable --now`, so the agents start now *and* auto-start whenever your user manager boots.

**Verify**:

```bash
systemctl --user is-enabled clearml-agent-frontier.service   # → enabled
systemctl --user status     clearml-agent-frontier.service   # → active (exited)
```

Test persistence: `exit`, ssh back in, and re-run `status` — uptime should predate your new login.

Service management commands:
```bash
CLIENT=frontier bash clients/.../launch_clearml_agent.sh --status-service
CLIENT=frontier bash clients/.../launch_clearml_agent.sh --stop-service
CLIENT=frontier bash clients/.../launch_clearml_agent.sh --start-service
CLIENT=frontier bash clients/.../launch_clearml_agent.sh --uninstall-service
```

## Slurm template hyperparameters

When submitting to the `frontier` (compute) queue, set these in the `properties` section:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `account` | OLCF allocation | `CSC708` |
| `partition` | Slurm partition | `batch` |
| `walltime` | Wall clock (HH:MM:SS) | `00:30:00` |
| `num_nodes` | Nodes | `1` |
| `ntasks_per_node` | MPI ranks per node | `8` |
| `gpus_per_node` | GPUs (GCDs) per node | `8` |
| `extra_sbatch` | Free-form extra `#SBATCH` directives, one per line. Use for `--reservation=`, `--qos=`, `--exclude=`, etc. | _(empty)_ |

**Reservation example.** To submit into the active csc708 reservation (partition `g1`, nodes `frontier[10177-10192]`):

```
properties.partition    = "g1"
properties.extra_sbatch = "#SBATCH --reservation=csc708-amsc-2"
```

The agent renders the template per-task, so the next sbatch picks up the change without restarting the agent.

## Known Frontier paths

| Filesystem | Path |
|-----------|------|
| Home | `/ccs/home/hzheng` |
| Orion (scratch) | `/lustre/orion/CSC708/proj-shared/hzheng` |

## Bug fix for clearml-agent v2.0.7

Apply the same `project_info` None-check fix as Perlmutter:

```bash
PYFILE=~/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/frontier/envs/clearml/lib/python3.*/site-packages/clearml_agent/helper/custom_template.py
cp $PYFILE ${PYFILE}.bak
sed -i 's/"PROJECT_NAME": project_info.get("name", "unknown")/"PROJECT_NAME": (project_info or {}).get("name", "unknown")/' $PYFILE
sed -i 's/"PROJECT_ID": project_info.get("id", "unknown")/"PROJECT_ID": (project_info or {}).get("id", "unknown")/' $PYFILE
```
