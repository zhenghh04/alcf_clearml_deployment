# Job launching tests

This folder contains example ClearML tasks that enqueue jobs onto ALCF queues and run simple payload scripts. It is meant to validate that ClearML agents can submit and run jobs correctly on login and compute queues.

## Python examples
Files under `tests/job_launching/python/` create ClearML tasks and enqueue them to queues:
- `test_login.py` Enqueue a small task to a login queue (example: `sirius-login`).
- `test_queue.py` Enqueue a compute job with PBS-related user properties (nodes, walltime, account).
- `test.py` Minimal payload script executed by the enqueued tasks.

Run an example:
```bash
python tests/job_launching/python/test_login.py
```

## Bash/PBS examples
Files under `tests/job_launching/bash/` mirror the Python flow but reference bash payload scripts:
- `test_login.py` Enqueue a login-queue task that runs `run_login.sh`.
- `test_queue.py` Enqueue a compute-queue task that runs `run.sh`.
- `run.sh` Example PBS/MPI payload.
- `run_login.sh` Example login-node payload.

## Notes
- Queue names and resource properties are site-specific; adjust for your ALCF system.
- These scripts assume your ClearML server/agent configuration is already in place.
