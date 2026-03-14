# `endpoint-config-json` Guide

This project supports passing per-submission endpoint overrides through:

- CLI: `clearml-globus-submit --endpoint-config-json '<json>'`
- Launcher API: `GlobusComputeLauncher.create(..., endpoint_config=<dict>)`

The payload is forwarded by `clearml_bridges/clearml_globus_bridge/submit_globus_job.py` to Globus Compute as `user_endpoint_config`.

## Core Rule

`endpoint-config-json` keys must match variables referenced by your endpoint `user_config_template.yaml.j2`.

In this repo's generated templates, these are flat keys (for example `num_nodes`, `cores_per_node`, `filesystems`, `init_blocks`), not nested provider objects.

## PBS Example

```bash
clearml-globus-submit \
  --endpoint-name crux-compute \
  --script /home/hzheng/clearml/alcf_clearml_deployment/examples/pipeline/globus_compute_bridge/tasks/globus_script.sh \
  --binary /bin/bash \
  --endpoint-config-json '{"account":"datascience","queue":"workq","walltime":"00:20:00","num_nodes":2,"cores_per_node":64,"filesystems":"home:eagle","place":"scatter","init_blocks":0,"min_blocks":0,"max_blocks":1}'
```

## Slurm Example

```bash
clearml-globus-submit \
  --endpoint-name my-slurm-endpoint \
  --script /path/to/script.sh \
  --binary /bin/bash \
  --endpoint-config-json '{"account":"datascience","partition":"debug","qos":"normal","walltime":"00:20:00","num_nodes":2,"cores_per_node":64,"gpus_per_node":0,"constraint":"","init_blocks":0,"min_blocks":0,"max_blocks":1}'
```

## Required Template Fields

Your `user_config_template.yaml.j2` must include:

- `engine.type`
- `engine.provider.type`

For PBS, example:

```yaml
engine:
  type: GlobusComputeEngine
  provider:
    type: PBSProProvider
    account: {{ account | default('datascience') }}
    queue: {{ queue | default('workq') }}
    walltime: {{ walltime | default('00:20:00') }}
    nodes_per_block: {{ num_nodes | default(2) }}
    init_blocks: {{ init_blocks | default(0) }}
    min_blocks: {{ min_blocks | default(0) }}
    max_blocks: {{ max_blocks | default(1) }}
    scheduler_options: |
      #PBS -l select={{ num_nodes | default(2) }}:ncpus={{ cores_per_node | default(64) }}
      #PBS -l place={{ place | default('scatter') }}
      #PBS -l walltime={{ walltime | default('00:20:00') }}
      #PBS -l filesystems={{ filesystems | default('home:eagle') }}
```

## Endpoint Environment Notes

- `endpoint_setup` should be top-level in the template.
- In endpoint YAML files, do not rely on shell expansion like `$PATH`.
- Use explicit `PATH` values in `user_environment.yaml`, for example:

```yaml
PATH: "/home/hzheng/clearml/miniconda3/bin:/opt/pbs/bin:/usr/bin:/bin"
```

## Common Failure Patterns

- `SEMANTICALLY_INVALID ... engine -> provider -> type field required`:
  - Missing `provider.type` in template.
- `qsub: command not found`:
  - Endpoint process PATH missing PBS client bin (`/opt/pbs/bin`).
- `ENDPOINT_NOT_ONLINE`:
  - UEP startup failed; inspect endpoint/UEP logs.
- Script `No such file or directory` for `/Users/...` path:
  - Local laptop path is not visible on endpoint host; use shared path or `--clone-repo true`.

## Verification Checklist

1. Submit once with `--endpoint-config-json`.
2. Inspect generated submit script in:
   - `~/.globus_compute/uep.<endpoint-id>.../submit_scripts/`
3. Confirm scheduler directives match expected values (`select`, `walltime`, `filesystems`, etc.).
4. For node placement, verify:
   - `qstat -f <jobid> | egrep "Resource_List.select|Resource_List.place|exec_vnode"`

