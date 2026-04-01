# ClearML IRI Bridge

`clearml_iri_bridge` provides ClearML-friendly wrappers for submitting work to facility APIs and reporting the resulting lifecycle back into ClearML.

Use `--facility` or `IRI_FACILITY` to select the target IRI deployment. Built-in mappings:

- `alcf` -> `https://api.alcf.anl.gov`
- `nersc` -> `https://api.nersc.gov`
- `olcf` -> `https://s3m.olcf.ornl.gov`

The current built-in submit/status defaults are the ALCF compute profile:

- `IRI_SUBMIT_PATH=/api/v1/compute/job/{system}`
- `IRI_STATUS_PATH_TEMPLATE=/api/v1/compute/status/{system}/{job_id}`
- `IRI_STATUS_FIELD=status.state`

The current default submit/status templates are still ALCF-oriented. For NERSC, OLCF, or another IRI deployment, also override any path templates and field mappings that differ there.

For `facility=alcf`, `--system` may be a friendly system name like `polaris` or `aurora`. The submit wrapper resolves that name to the underlying ALCF compute resource id before calling `/api/v1/compute/*`.

## Install

From repository root:

```bash
pip install -e .
```

## CLI Tools

- `clearml-iri-launch`: create and optionally enqueue a ClearML task that will submit work to the IRI API
- `clearml-iri-submit`: run the IRI submit/poll flow inside a ClearML task
- `clearml-iri-transfer`: run shell-based data movement (`rsync`, `scp`, or `cp`) inside a ClearML task
- `clearml-iri-transfer-launch`: create and optionally enqueue a ClearML data movement task

## Data Movement

Run data movement directly:

```bash
clearml-iri-transfer \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "stage-data-to-eagle" \
  --transport rsync \
  --src-path /tmp/source-dir/ \
  --dst-path /eagle/datascience/hzheng/stage/ \
  --recursive
```

Create and enqueue a transfer task:

```bash
clearml-iri-transfer-launch \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "stage-data-to-eagle" \
  --transport rsync \
  --src-path /tmp/source-dir/ \
  --dst-path /eagle/datascience/hzheng/stage/ \
  --recursive \
  --queue crux-services \
  --tags-json '["iri-transfer"]'
```

## Create And Enqueue A Task

Create a payload file:

```bash
cat > /tmp/iri_payload.json <<'JSON'
{
  "name": "clearml-iri-job",
  "executable": "/bin/bash",
  "arguments": ["-lc", "echo hello from ClearML IRI bridge"],
  "directory": "/eagle/datascience/hzheng/",
  "stdout_path": "/eagle/datascience/hzheng/iri.out",
  "stderr_path": "/eagle/datascience/hzheng/iri.err",
  "attributes": {
    "account": "AmSC_Demos",
    "queue_name": "debug"
  }
}
JSON
```

Then launch:

```bash
clearml-iri-launch \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "submit-iri-job" \
  --working-directory . \
  --facility alcf \
  --system polaris \
  --job-payload-file /tmp/iri_payload.json \
  --queue crux-services \
  --tags-json '["iri-bridge"]'
```

`clearml-iri-launch` reads `--job-payload-file` locally at launch time and embeds the JSON into the created ClearML task. It does not rely on that file path existing on the remote worker.
Pass `--repo` and `--branch` only when the ClearML task should be tied to a specific Git repository checkout.

## Run The Submit Wrapper Directly

```bash
export IRI_FACILITY=alcf
export IRI_API_TOKEN=<token>
export IRI_SYSTEM=aurora

clearml-iri-submit \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "submit-iri-job" \
  --job-payload-file /tmp/iri_payload.json \
  --log-stdout \
  --log-stderr
```

By default, the bridge reads the submitted `stdout_path` and `stderr_path` after the job reaches a terminal state and prints them into the ClearML console. Use `--max-log-chars` to cap how much is emitted from each file. You can disable the default behavior by exporting `IRI_LOG_STDOUT=0` and/or `IRI_LOG_STDERR=0`.

When `stdout_path` and `stderr_path` exist and are readable by the ClearML worker, the bridge also uploads them automatically as ClearML artifacts:

- `iri_stdout`
- `iri_stderr`

## Known Issues

- ALCF output and error paths under `/eagle/...` are currently unreliable when jobs are submitted through the facility API service nodes. Based on discussion with the ALCF team, the `facility-api-vmw-*` VMs do not mount Eagle, and jobs submitted from that path may not generate `stdout_path` and `stderr_path` files on Eagle even though the job itself completes.
- For ALCF, output and error files are more reliable when written to the user's home directory, for example `/home/<user>/...`, instead of `/eagle/...`.
- The hostname shown in PBS `Output_Path` and `Error_Path` reflects the host that submitted the request. For facility API submissions this may appear as `facility-api-vmw-01...`, while login-node submissions may show `polaris-login-01...`.
- The bridge helper supports `resources.node_count` through `build_job_payload(..., node_count=...)`. Existing `note_count` callers are still accepted as a compatibility alias and mapped to `node_count`.

## Python API

```python
from clearml import Task
from clearml_iri_bridge import IRILauncher

launcher = IRILauncher()
submit_task = launcher.create(
    project_name="AmSC/pipeline-iri-bridge",
    task_name="submit-iri-job-step",
    task_type=Task.TaskTypes.data_processing,
    repo="https://github.com/argonne-lcf/alcf_clearml_deployment.git",
    branch="main",
    working_directory=".",
    facility="alcf",
    system="aurora",
    job_payload={
        "name": "clearml-iri-job",
        "executable": "/bin/bash",
        "arguments": ["-lc", "echo hello from ClearML IRI bridge"],
        "attributes": {"queue_name": "debug-scaling"},
    },
    tags=["iri-bridge"],
)
```

For shell-based job payloads, `IRILauncher.create(...)` also prepends a default job-side repo checkout step when `repo=...` is provided. The injected precommand creates the payload `directory`, clones the repository there if needed, and then changes into the cloned checkout before the main command or script runs. Pass `clone_repo_on_job=False` to disable that behavior.

## Environment

Required:

- `IRI_FACILITY`
- `IRI_API_TOKEN`
- `IRI_SYSTEM`

Common overrides:

- `IRI_SUBMIT_PATH`
- `IRI_STATUS_PATH_TEMPLATE`
- `IRI_RESULT_PATH_TEMPLATE`
- `IRI_JOB_ID_FIELD`
- `IRI_STATUS_FIELD`
- `IRI_RESULT_FIELD`

Facility note:

- `IRI_FACILITY` selects the facility endpoint.
- Supported built-ins are `alcf`, `nersc`, and `olcf`.
- The default submit/status templates in this package currently match ALCF.
- For OLCF, NERSC, or another deployment whose schema differs from ALCF, set the facility-specific `IRI_SUBMIT_PATH`, `IRI_STATUS_PATH_TEMPLATE`, and status/id field mappings.
