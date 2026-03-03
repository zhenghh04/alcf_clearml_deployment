# clearml_globus_bridge

`clearml_globus_bridge` is the bridge package that connects ClearML tasks/pipelines to Globus Compute endpoints.

It provides:
- A launcher helper (`GlobusComputeLauncher`) to create ClearML tasks that submit work to Globus Compute.
- A submit wrapper CLI (`clearml-globus-submit`) that executes payloads on a Globus endpoint and reports results back to ClearML.
- A token helper CLI (`clearml-globus-token`) that exports `GLOBUS_COMPUTE_ACCESS_TOKEN`.
- An endpoint discovery CLI (`clearml-globus-endpoints`) to list endpoints visible to your identity.
- Endpoint config helpers for PBS/Slurm (`clearml-globus-configure-pbs-endpoint`, `clearml-globus-configure-slurm-endpoint`).

## Install

From repository root:

```bash
pip install -e .
```

## How to use

### 1) Submit directly with CLI

Set endpoint and ClearML context, then run:

```bash
export GLOBUS_COMPUTE_ENDPOINT_ID=<endpoint-id>
clearml-globus-submit \
  --project-name "AmSC/pipeline-globus-bridge" \
  --task-name "submit-globus-job" \
  --task-type data_processing
```

Default behavior runs a simple remote function (`input * input`) on the endpoint.

To execute a script on the endpoint:

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

For non-interactive auth, pass an access token directly:

```bash
eval "$(clearml-globus-token)"

clearml-globus-submit \
  --endpoint-id "$GLOBUS_COMPUTE_ENDPOINT_ID" \
  --token "$GLOBUS_COMPUTE_ACCESS_TOKEN"
```

You can also set `GLOBUS_COMPUTE_ACCESS_TOKEN` instead of `--token`.

List endpoints you can access:

```bash
clearml-globus-endpoints --role any
clearml-globus-endpoints --role owner --json
clearml-globus-endpoints --token "$GLOBUS_COMPUTE_ACCESS_TOKEN"
```

### 2) Use from Python (recommended in pipelines)

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
    endpoint_name="crux-compute",  # or endpoint_id="..."
    script="/path/on/endpoint/job.sh",  # optional; omit for default function payload
    binary="/bin/bash",
    poll_interval=5,
    timeout_sec=900,
    tags=["globus-bridge"],
)
```

Then use `submit_task.id` in a `PipelineController` step.

## Endpoint config helpers

Generate/update endpoint templates:

```bash
clearml-globus-configure-pbs-endpoint --endpoint-name my-pbs-endpoint
clearml-globus-configure-slurm-endpoint --endpoint-name my-slurm-endpoint
```

These commands create/update `config.yaml` and `user_config_template.yaml.j2` under `~/.globus_compute/<endpoint-name>/`.

## Related examples

- `examples/pipeline/globus_compute_bridge/pipeline.py`
- `examples/pipeline/globus_compute_bridge/bridge_worker.py`
- `examples/pipeline/globus_compute_bridge/README.md`
