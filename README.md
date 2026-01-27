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
Python enqueue examples: `tests/job_launching/python/test_login.py`, `tests/job_launching/python/test_queue.py`, `tests/job_launching/python/test.py`.
Bash/PBS examples: `tests/job_launching/bash/test_login.py`, `tests/job_launching/bash/test_queue.py`, `tests/job_launching/bash/run.sh`, `tests/job_launching/bash/run_login.sh`.

Example:
```bash
python tests/job_launching/python/test_login.py
```

### Pipelines
Files: `tests/pipeline/pipeline_from_decorator.py`, `tests/pipeline/pipeline_from_functions.py`, `tests/pipeline/pipeline_different_systems.py`, `tests/pipeline/hpc_pipeline_demo/`.

### Experiment tracking
File: `tests/experiment_tracking/pytorch_mnist.py`.

### Datasets
Files: `tests/data/test_creation.py`, `tests/data/test_upload_link.py`, `tests/data/dolma.py`.

## Notes
- Many scripts assume ClearML server URLs, queues, and filesystem paths that are specific to ALCF environments. Adjust as needed for your site.
