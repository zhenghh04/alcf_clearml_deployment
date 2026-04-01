# IRI Launch Examples

This directory shows how to launch an IRI-backed job through the ClearML IRI bridge.

Available examples:

- CLI example: [cli/run.sh](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/cli/run.sh)
- Python example: [python/launch_iri_job.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/launch_iri_job.py)
- Stage-in with Globus example: [python/iri_stage_with_globus.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus.py)
- Stage-in with Globus pipeline: [python/iri_stage_with_globus_pipeline.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus_pipeline.py)
- Local Globus setup: [python/LOCAL_GLOBUS_TRANSFER_SETUP.md](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/LOCAL_GLOBUS_TRANSFER_SETUP.md)

## Prerequisites

- `clearml-iri-launch` installed in the Python environment you are using
- ClearML configured for your server
- `IRI_API_TOKEN` available on the worker that will run `clearml_iri_bridge.submit_iri_job`
- access to the target facility account and filesystem paths

Install the package from repository root if needed:

```bash
python3 -m pip install -e /Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment
```

## CLI Example

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

Then run:

```bash
./cli/run.sh
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

You can also provide script content instead of embedding `arguments` in the payload. For example:

```bash
clearml-iri-launch \
  --project-name "AmSC/pipeline-iri-bridge" \
  --task-name "submit-iri-job-script" \
  --repo https://github.com/zhenghh04/alcf_clearml_deployment.git \
  --branch main \
  --working-directory . \
  --facility alcf \
  --system polaris \
  --job-payload-file /tmp/iri_payload.json \
  --script-file ./job.sh \
  --queue crux-services
```

`--script` and `--script-file` are converted by the bridge into the standard:

- `executable: /bin/bash`
- `arguments: ["-lc", "<script contents>"]`

Notes:

- `stdout_path` and `stderr_path` are required by the ALCF API.
- ALCF also requires a walltime/duration value. This example uses `duration: 300`.
- `system=polaris` is resolved automatically by the bridge to the ALCF compute resource ID.

## Python Example

The Python launcher example is here:

- [python/launch_iri_job.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/launch_iri_job.py)

It uses the bridge helper `build_job_payload(...)` so you do not need to hand-write the payload JSON:

```python
from clearml import Task
from clearml_iri_bridge import IRILauncher, build_job_payload

launcher = IRILauncher()
job_payload = build_job_payload(
    scheduler="pbs",
    directory="/eagle/datascience/hzheng/",
    stdout_path="/eagle/datascience/hzheng/iri.out",
    stderr_path="/eagle/datascience/hzheng/iri.err",
    account="AmSC_Demos",
    queue_name="debug",
    duration=300,
    command="echo hello from ClearML IRI bridge",
)

submit_task = launcher.create(
    project_name="AmSC/pipeline-iri-bridge",
    task_name="submit-iri-job",
    task_type=Task.TaskTypes.data_processing,
    repo="https://github.com/zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory=".",
    facility="alcf",
    system="polaris",
    job_payload=job_payload,
    tags=["iri-bridge"],
)

Task.enqueue(submit_task, queue_name="crux-services")
```

`build_job_payload(...)` currently supports:

- `scheduler="pbs"`
- `scheduler="slurm"`
- `command="..."`
- `script="..."`
- `script_path="/path/to/job.sh"`
- `script_remote_path="/eagle/.../job.sh"`
- `arguments=[...]`
- `custom_attributes={...}`
- `extra_attributes={...}`

For ALCF specifically, a short inline `command` is usually fine, but sending a long script body through the API can trigger upstream filtering. The more reliable pattern is:

- make the script available on the remote filesystem
- submit with `script_path="relative/path/to/job.sh"` or `script_path="/absolute/path/on/remote/job.sh"`

The example [iri_submit_script.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_submit_script.py) now uses that mode.

If the script starts on your local machine and must be staged to the facility first, use the Globus stage-in example:

- [iri_stage_with_globus.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus.py)
- [iri_stage_with_globus_pipeline.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus_pipeline.py)
- [LOCAL_GLOBUS_TRANSFER_SETUP.md](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/LOCAL_GLOBUS_TRANSFER_SETUP.md)

Start with the setup note if your source file lives on your laptop or desktop and needs to be transferred through Globus before the IRI job can run.

The simple stage-in example:

- creates and enqueues a `GlobusDataMover` task to copy the local file to the remote destination
- creates the IRI submit task pointing `script_path` at the staged remote file
- prints both task URLs so you can enqueue the IRI task after the transfer completes
- uses explicit Python constants at the top of the file for endpoints, paths, and queues instead of environment variables

The pipeline variant:

- creates the same transfer task and IRI submit task templates
- wires them together in a `PipelineController`
- runs the transfer step first and the IRI step second
- starts the pipeline on the configured controller queue automatically

For script-based launches, the bridge now uses a login shell path so the runtime is closer to normal PBS `qsub` behavior:

- remote scripts are launched as `/bin/bash -l <script>`
- inline commands and inline scripts are launched through `bash -lc`
- the bundled example [job.sh](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/job.sh) also uses `#!/bin/bash -l`

This matters because tools such as `module`, `conda`, `python`, and `mpiexec` may not be available in a plain non-login shell.

Expected output includes:

```text
Enqueued task: <task_id> on queue crux-services
ClearML results page: https://.../projects/<project_id>/experiments/<task_id>/output/log
```

## Worker Notes

- `clearml-iri-launch` reads `--job-payload-file` locally and stores the payload in the created task.
- Existing tasks created before recent bridge fixes may still have empty payloads. Create a new task after updating the package.
- If submit fails, check the ClearML log for:
  - `[iri] payload_source=...`
  - `[iri] payload=...`
  - `[iri] system=... resolved_system=...`
  - response body details from the facility API

## Known Issues

- On ALCF, `stdout_path` and `stderr_path` under `/eagle/...` may not appear when the job is submitted through the facility API service nodes such as `facility-api-vmw-01...`.
- Current ALCF guidance is to prefer home-directory output paths such as `/home/<user>/iri.out` and `/home/<user>/iri.err` if you want the files to be generated reliably.
- The bridge can only upload stdout and stderr artifacts when those files are visible from the ClearML worker. If the files are not generated or are not mounted on the worker host, artifact upload will be skipped.
- The example payloads now use `resources.note_count` when requesting compute resources through the IRI API.
