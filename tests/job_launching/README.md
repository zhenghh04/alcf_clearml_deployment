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

## Pattern B: single allocation with local ClearML subtasks
This pattern submits **one** ClearML task to the queue (one PBS allocation), then launches multiple
local ClearML subtasks inside that same job. Each subtask is a separate process, but **no additional
queue submissions** are made.

**Files:**
- `tests/job_launching/pattern_b/submit_pattern_b.py` (enqueue the single allocation)
- `tests/job_launching/pattern_b/run_local_tasks.py` (runs inside the allocation)
- `tests/job_launching/pattern_b/subtask_worker.py` (example subtask)

**Run:**
```bash
python tests/job_launching/pattern_b/submit_pattern_b.py --queue crux --num-nodes 6
```

Inside the job, `run_local_tasks.py` reads `PBS_NODEFILE` (or `COBALT_NODEFILE`), splits
the nodes into groups (default 2 nodes per subtask), and launches the subtasks locally.

## Notes
- Queue names and resource properties are site-specific; adjust for your ALCF system.
- These scripts assume your ClearML server/agent configuration is already in place.
