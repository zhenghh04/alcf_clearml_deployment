# ClearML Globus Bridege

`clearml_globus_bridge` provides ClearML-friendly wrappers for:
- Globus Compute task submission
- Globus Transfer data movement
- Endpoint configuration helpers

## Install

From repository root:

```bash
pip install -e .
```

## CLI Tools

- `clearml-globus-submit`: submit/poll Globus Compute work
- `clearml-globus-configure-pbs-endpoint`: generate/update PBS endpoint config templates
- `clearml-globus-configure-slurm-endpoint`: generate/update Slurm endpoint config templates
- `clearml-globus-token`: export Compute or Transfer access token (`--type compute|transfer`)
- `clearml-globus-endpoints`: list endpoints visible to your identity
- `clearml-globus-auth`: create + enqueue a ClearML task that runs Globus auth on an agent
- `clearml-globus-transfer`: run Globus Transfer data movement
- `clearml-globus-transfer-launch`: create + enqueue a ClearML transfer task

## Configuration (Env Vars)

| Variable | Used by | Purpose |
|---|---|---|
| `GLOBUS_COMPUTE_ENDPOINT_ID` | `clearml-globus-submit` | Target Globus Compute endpoint ID |
| `GLOBUS_COMPUTE_ENDPOINT_NAME` | `clearml-globus-submit` | Target endpoint name (resolved to ID) |
| `GLOBUS_COMPUTE_ACCESS_TOKEN` | `clearml-globus-submit`, `clearml-globus-endpoints` | Non-interactive Compute auth token |
| `GLOBUS_TRANSFER_ACCESS_TOKEN` | `clearml-globus-transfer` | Non-interactive Transfer auth token |
| `GLOBUS_TRANSFER_ACCESS_TOKEN_ENV` | transfer CLIs | Env var name containing Transfer token (default: `GLOBUS_TRANSFER_ACCESS_TOKEN`) |
| `GLOBUS_SRC_ENDPOINT`, `GLOBUS_DST_ENDPOINT` | transfer CLIs | Source/destination collection/endpoint |
| `GLOBUS_SRC_PATH`, `GLOBUS_DST_PATH` | transfer CLIs | Source/destination path |
| `GLOBUS_SYNC_LEVEL` | transfer CLIs | Transfer sync behavior |
| `GLOBUS_POLL_INTERVAL` | transfer CLIs | Poll interval (seconds) |

CLI args override environment variables.

## Globus Compute (CLI)

Submit default payload:

```bash
export GLOBUS_COMPUTE_ENDPOINT_ID=<endpoint-id>
clearml-globus-submit \
  --project-name "AmSC/pipeline-globus-bridge" \
  --task-name "submit-globus-job" \
  --task-type data_processing
```

Submit a script:

```bash
clearml-globus-submit \
  --project-name "AmSC/pipeline-globus-bridge" \
  --task-name "submit-globus-script" \
  --task-type data_processing \
  --endpoint-id "$GLOBUS_COMPUTE_ENDPOINT_ID" \
  --script /path/on/endpoint/job.sh \
  --binary /bin/bash \
  --script-args-json '["--arg1","value1"]'
```

Token-based Compute auth:

```bash
eval "$(clearml-globus-token --type compute)"
clearml-globus-submit --endpoint-id "$GLOBUS_COMPUTE_ENDPOINT_ID" --token "$GLOBUS_COMPUTE_ACCESS_TOKEN"
```

List Compute endpoints:

```bash
clearml-globus-endpoints --role any
clearml-globus-endpoints --role owner --json
clearml-globus-endpoints --token "$GLOBUS_COMPUTE_ACCESS_TOKEN"
```

Queue-based auth on an agent:

```bash
clearml-globus-auth \
  --type transfer \
  --queue crux-services \
  --project-name AmSC \
  --task-name "Globus auth on crux-services" \
  --follow
```

Then open the queued task logs and complete the URL/device-code login flow in your local browser.

If the worker has no interactive stdin, complete transfer auth in two steps:

```bash
# Step 1: run once to get URL from task logs
clearml-globus-auth --type transfer --queue crux-services --follow

# Step 2: rerun with one-time Authorization Code copied from browser
clearml-globus-auth --type transfer --queue crux-services --auth-code "<AUTH_CODE>" --follow
```

Single-command helper (runs both steps and prompts locally for auth code):

```bash
clearml-globus-auth --type transfer --queue crux-services --one-shot
```

## Globus Transfer (CLI)

Run transfer directly:

```bash
clearml-globus-transfer \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path /datasets/test.txt \
  --dst-path /datascience/test.txt \
  --recursive
```

Token-based Transfer auth (no CLI login state required on worker):

```bash
eval "$(clearml-globus-token --type transfer)"

clearml-globus-transfer \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path /datasets/test.txt \
  --dst-path /datascience/test.txt \
  --token-env-var GLOBUS_TRANSFER_ACCESS_TOKEN
```

Create and enqueue transfer task:

```bash
clearml-globus-transfer-launch \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path /datasets/test.txt \
  --dst-path /datascience/test.txt \
  --token-env-var GLOBUS_TRANSFER_ACCESS_TOKEN \
  --queue sirius-login
```

## Python API

Globus Compute task creation:

```python
from clearml import Task
from clearml_globus_bridge import GlobusComputeLauncher

launcher = GlobusComputeLauncher()
submit_task = launcher.create(
    project_name="AmSC/pipeline-globus-bridge",
    task_name="globus-submit-step",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:your-org/your-repo.git",
    branch="main",
    working_directory=".",
    endpoint_name="crux-compute",
    script="/path/on/endpoint/job.sh",
    binary="/bin/bash",
    poll_interval=5,
    timeout_sec=900,
)
```

Globus Transfer task creation:

```python
import os
from clearml_globus_bridge import GlobusDataMover

mover = GlobusDataMover()
transfer_task = mover.create(
    project_name="AmSC/data-movement",
    task_name="transfer-step",
    src_endpoint="alcf#dtn_eagle",
    dst_endpoint="alcf#dtn_flare",
    src_path="/datasets/test.txt",
    dst_path="/datascience/test.txt",
    recursive=True,
    token_env_var="GLOBUS_TRANSFER_ACCESS_TOKEN",
)
```

`create(...)` returns a ClearML `Task` object. Enqueue it with `Task.enqueue(...)` in your pipeline/controller flow.

## Endpoint Config Helpers

Generate/update endpoint templates:

```bash
clearml-globus-configure-pbs-endpoint --endpoint-name my-pbs-endpoint
clearml-globus-configure-slurm-endpoint --endpoint-name my-slurm-endpoint
```

These commands create/update `config.yaml` and `user_config_template.yaml.j2` under `~/.globus_compute/<endpoint-name>/`.

## Related Examples

- `examples/pipeline/globus_compute_bridge/pipeline.py`
- `examples/pipeline/globus_compute_bridge/bridge_worker.py`
- `examples/pipeline/globus_compute_bridge/README.md`
- `examples/data_movement/README.md`
