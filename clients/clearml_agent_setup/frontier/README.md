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
