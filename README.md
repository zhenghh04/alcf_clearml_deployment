# ClearML Evaluation on ALCF systems

Author: Huihuo Zheng

This repository contains setup scripts and example tests for evaluating ClearML (server + agents) on ALCF systems. It includes server setup notes/scripts, client/agent scripts and templates for different ALCF systems, and example tests for job launching, pipelines, experiment tracking, and datasets.

## Repository layout
- `server/` ClearML server setup notes and scripts.
- `clients/` Agent install and launch scripts plus PBS templates and configs.
- `tests/` Example ClearML workflows and tests.

## Setup scripts

### ClearML server (VM)
Files: `server/README.md`, `server/setup.sh`.
Typical flow (from `server/README.md`): provision a VM and open ports 8080/8081/8001, copy ClearML-provided `docker-compose.yml`, `docker-compose.override.yml`, and `constants.env` into `/opt/allegro/`, run `server/setup.sh`, then recompose via `docker-compose`.

### ClearML agent (client)
Files: `clients/install_clearml.sh`, `clients/launch_clearml_agent.sh`, `clients/*/pbs.template`, `clients/*/clearml.conf`.
Use `clients/install_clearml.sh` to install `clearml-agent-slurm` and `clearml-agent`, then `clients/launch_clearml_agent.sh` to start agents using PBS templates and a target queue.

### Test environment setup
File: `tests/setup.sh`. This exports environment variables commonly used on ALCF systems (proxy, OpenBLAS, ClearML agent config).

## Testing scripts
There is no single test runner; run the individual scripts in `tests/` as needed.

### Job launching
* Python enqueue examples: 
    - `tests/job_launching/python/test_login.py`: run tasks on login node through clearml-agent queue
    - `tests/job_launching/python/test_queue.py`: run tasks on compute node(s) through clearml-slurm-agent queue
* Bash/PBS examples: 
    - `tests/job_launching/bash/test_login.py` & `tests/job_launching/bash/run_login.sh`: run tasks on login node with the steps defined in run_login.sh
    - `tests/job_launching/bash/test_queue.py` & `tests/job_launching/bash/run.sh`, run tasks on compute node(s) with the steps defined in run.sh

Example submission: 
```bash
python tests/job_launching/python/test_login.py
```

### Pipelines
- `tests/pipeline/pipeline_from_decorator.py` Pipeline built with `PipelineDecorator` components.
- `tests/pipeline/pipeline_from_functions.py` Pipeline built with `PipelineController` function steps.
- `tests/pipeline/pipeline_different_systems.py` Multi-queue pipeline example for different systems.
- `tests/pipeline/hpc_pipeline_demo/` End-to-end HPC pipeline demo with data prep, train, and eval.

### Experiment tracking
- `tests/experiment_tracking/pytorch_mnist.py` ClearML experiment tracking example (MNIST).

### Datasets
- `tests/data/test_creation.py` Create and upload a dataset to ClearML.
- `tests/data/test_upload_link.py` Add external files to a dataset via file links.
- `tests/data/dolma.py` Register Dolma dataset files as external links.

## Notes
- Many scripts assume ClearML server URLs, queues, and filesystem paths that are specific to ALCF environments. Adjust as needed for your site.

## Globus Compute PBS Config Helper

Use this helper to generate/update endpoint files for PBS-based Globus Compute endpoints:

```bash
clearml-globus-configure-pbs-endpoint \
  --endpoint-name aurora-user \
  --account datascience \
  --queue debug \
  --walltime 00:10:00 \
  --nodes-per-block 1 \
  --cores-per-node 64 \
  --filesystems flare:home \
  --overwrite --backup
```

This writes:
- `~/.globus_compute/<endpoint-name>/config.yaml`
- `~/.globus_compute/<endpoint-name>/user_config_template.yaml.j2`

For Slurm-based endpoints:

```bash
clearml-globus-configure-slurm-endpoint \
  --endpoint-name perlmutter-user \
  --account m1234 \
  --partition regular \
  --qos normal \
  --walltime 00:30:00 \
  --nodes-per-block 1 \
  --cores-per-node 64 \
  --gpus-per-node 4 \
  --overwrite --backup
```

## IRI API Bridge

This repo now also includes an IRI-compatible connector:
- Python module: `clearml_iri_bridge`
- CLI submit wrapper: `clearml-iri-submit`
- Example pipeline: `tests/pipeline/iri_bridge/pipeline.py`

This connector is designed for APIs like `https://api.iri.nersc.gov` and accepts configurable submit/status paths and response field mappings.
