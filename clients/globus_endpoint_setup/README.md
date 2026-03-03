# Globus Compute Endpoint Setup

This folder contains helper scripts and reference files for setting up and using personal Globus endpoints (Compute and Transfer), especially for ClearML pipelines in this repository.

Files in this folder:
- `ssh_proxy.sh`: opens a SOCKS proxy for environments that require a login-host network hop.
- `ssh_tunnel_clearml.sh`: opens an SSH tunnel to a named SSH target from your local SSH config.
- `compute.env.example`: example environment profile for Globus Compute submissions.
- `transfer.env.example`: example environment profile for Globus Transfer submissions.
- `ENDPOINT_CONFIG_JSON.md`: mapping and examples for `--endpoint-config-json`.

## 1) Prerequisites

Install and verify:

```bash
python3 -m pip install -e .
python3 -m pip install globus-compute-endpoint globus-compute-sdk
globus-compute-endpoint version
```

You also need:
- A reachable login host on the target HPC system.
- Scheduler access (PBS or Slurm) on that system.
- Valid Globus authentication for your user.

## 2) Optional connectivity helpers to connect to ClearML server

If you need proxy/tunnel access from your laptop:

SOCKS proxy:
```bash
bash clients/globus_endpoint_setup/ssh_proxy.sh
export HTTP_PROXY="socks5h://127.0.0.1:3128"
export HTTPS_PROXY="socks5h://127.0.0.1:3128"
```

SSH tunnel using a host alias from `~/.ssh/config`:
```bash
SSH_TUNNEL_TARGET=clearml bash clients/globus_endpoint_setup/ssh_tunnel_clearml.sh
```

You can persist `SSH_TUNNEL_TARGET` by creating:
- `clients/globus_endpoint_setup/.env`

## 3) Create a personal Globus Compute endpoint

Authenticate first:
```bash
globus-compute-endpoint login
```

### PBS endpoint (for ALCF systems)

```bash
clearml-globus-configure-pbs-endpoint \
  --endpoint-name <your-endpoint-name> \
  --account <allocation> \
  --queue <queue> \
  --walltime 00:10:00 \
  --nodes-per-block 1 \
  --cores-per-node 64 \
  --filesystems flare:home \
  --overwrite --backup
```

This writes:
- `~/.globus_compute/<your-endpoint-name>/config.yaml`
- `~/.globus_compute/<your-endpoint-name>/user_config_template.yaml.j2`

### Slurm endpoint (for OLCF and NERSC systems)

```bash
clearml-globus-configure-slurm-endpoint \
  --endpoint-name <your-endpoint-name> \
  --account <allocation> \
  --partition <partition> \
  --qos <qos> \
  --walltime 00:10:00 \
  --nodes-per-block 1 \
  --cores-per-node 64 \
  --gpus-per-node 0 \
  --overwrite --backup
```

Notes:
- The generated template includes `provider.type`, which is required by Globus Compute.
- Helpers also set explicit `PATH` in `endpoint_setup` so scheduler commands are visible.

## 4) Start and verify endpoint

Start endpoint:
```bash
globus-compute-endpoint start <your-endpoint-name>
```

Check status:
```bash
globus-compute-endpoint list
globus-compute-endpoint status <your-endpoint-name>
```

Get endpoint ID (used by jobs/pipelines):
```bash
globus-compute-endpoint list | grep <your-endpoint-name>
```

Stop/restart when needed:
```bash
globus-compute-endpoint stop <your-endpoint-name>
globus-compute-endpoint start <your-endpoint-name>
```

## 5) Test submission from this repo

Minimal test via bridge submit wrapper:
```bash
clearml-globus-submit \
  --project-name "AmSC/pipeline-globus-bridge" \
  --task-name "globus-endpoint-smoke-test" \
  --task-type data_processing \
  --endpoint-id <endpoint-id>
```

Script execution test:
```bash
clearml-globus-submit \
  --project-name "AmSC/pipeline-globus-bridge" \
  --task-name "globus-endpoint-script-test" \
  --task-type data_processing \
  --endpoint-name <your-endpoint-name> \
  --script /path/on/endpoint/job.sh \
  --binary /bin/bash \
  --script-args-json '["--arg1","value1"]'
```

## 6) Per-submission resource overrides

Use `--endpoint-config-json` to override scheduler values at submit time:

```bash
clearml-globus-submit \
  --endpoint-name <your-endpoint-name> \
  --script /path/on/endpoint/job.sh \
  --binary /bin/bash \
  --endpoint-config-json '{"account":"datascience","queue":"debug","walltime":"00:20:00","num_nodes":2,"cores_per_node":64}'
```

Reference and key mapping details:
- `clients/globus_endpoint_setup/ENDPOINT_CONFIG_JSON.md`

Environment profile examples:
- `clients/globus_endpoint_setup/compute.env.example`
- `clients/globus_endpoint_setup/transfer.env.example`

## 7) Troubleshooting

- `SEMANTICALLY_INVALID ... provider -> type field required`:
  your endpoint template is missing `provider.type`; regenerate with helper scripts.
- `qsub: command not found` or `sbatch: command not found`:
  scheduler binaries are not on endpoint PATH; adjust `--scheduler-bin-dir` and restart endpoint.
- `ENDPOINT_NOT_ONLINE`:
  endpoint process failed to start; check endpoint logs under `~/.globus_compute/<endpoint-name>/`.
- Script path errors (`No such file or directory`):
  local laptop paths are not visible on the endpoint host; use a shared filesystem path.

## 8) Related docs

- Bridge package guide: `clearml_bridges/clearml_globus_bridge/README.md`
- Pipeline usage example: `examples/pipeline/globus_compute_bridge/README.md`
