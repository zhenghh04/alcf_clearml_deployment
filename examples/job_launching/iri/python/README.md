# IRI CLI Example

This example shows how to launch an ALCF IRI job through `clearml-iri-launch`.

## Prerequisites

- `clearml-iri-launch` installed in the Python environment you are using
- ClearML configured for your server
- `IRI_API_TOKEN` available on the worker that will run `clearml-iri-submit`
- access to the target ALCF account and filesystem paths

Install the package from repository root if needed:

```bash
python3 -m pip install -e /Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment
```

## Payload File

Write the job payload to a local file:

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
    "queue_name": "debug",
    "duration": 300,
    "custom_attributes": {
      "filesystems": "home:eagle"
    }
  }
}
JSON
```

Notes:

- `stdout_path` and `stderr_path` are required by the ALCF API.
- ALCF also requires a walltime/duration value. This example uses `duration: 300`.
- `system=polaris` is resolved automatically by the bridge to the underlying ALCF compute resource ID.

## Launch

Run:

```bash
./run.sh
```

Or directly:

```bash
clearml-iri-launch \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "submit-iri-job" \
  --repo https://github.com/zhenghh04/alcf_clearml_deployment.git \
  --branch main \
  --working-directory . \
  --facility alcf \
  --system polaris \
  --job-payload-file /tmp/iri_payload.json \
  --queue crux-services \
  --tags-json '["iri-bridge"]'
```

## Python Example

A matching Python launcher example is available at:

- [launch_iri_job.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/launch_iri_job.py)

It reads `/tmp/iri_payload.json`, creates the task with `IRILauncher`, enqueues it on `crux-services`, and prints the ClearML results URL.

The bridge also provides a helper for Python callers:

```python
from clearml_iri_bridge import IRILauncher, build_alcf_job_payload

payload = build_alcf_job_payload(
    name="clearml-iri-job",
    directory="/eagle/datascience/hzheng/",
    stdout_path="/eagle/datascience/hzheng/iri.out",
    stderr_path="/eagle/datascience/hzheng/iri.err",
    account="AmSC_Demos",
    queue_name="debug",
    duration=300,
    command="echo hello from ClearML IRI bridge",
)

launcher = IRILauncher()
task = launcher.create(
    project_name="AmSC/pipeline-iri-bridge",
    task_name="submit-iri-job",
    repo="https://github.com/zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory=".",
    facility="alcf",
    system="polaris",
    job_payload=payload,
)
```

Expected output includes:

```text
Enqueued task: <task_id> on queue crux-services
ClearML results page: https://.../projects/<project_id>/experiments/<task_id>/output/log
```

## Worker Notes

- `clearml-iri-launch` reads `--job-payload-file` locally and stores the payload in the created task.
- Existing tasks created before recent bridge fixes may still have empty payloads. Create a new task after updating the package.
- If submit fails, check the ClearML log for:
  - `[iri] payload=...`
  - `[iri] system=... resolved_system=...`
  - ALCF response body details
