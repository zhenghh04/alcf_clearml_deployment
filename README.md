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
