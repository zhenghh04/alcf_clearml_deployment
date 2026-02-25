import os
import shlex

from clearml import PipelineController, Task
from clearml_globus_bridge.globus_compute_launcher import GlobusComputeLauncher

# Scheduler/resource settings are intentionally configured in-code
# (not via environment variables) to keep runs reproducible.
def _env_optional(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    normalized = value.strip()
    if normalized.lower() in {"", "none", "null"}:
        return None
    return normalized


def main() -> None:
    launcher = GlobusComputeLauncher()
    submit_task = launcher.create(
        project_name="AmSC/pipeline-globus-bridge-zhenghh",
        task_name="crux-globus",
        task_type=Task.TaskTypes.data_processing,
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory="./tests/pipeline/globus_compute_bridge",
        # Run launcher task from repo root so module mode + `packages=["-e ."]` works.
        launcher_working_directory=".",
        script_working_directory=_env_optional("GLOBUS_SCRIPT_WORKING_DIRECTORY"),
        endpoint_name="crux-compute",
        script="/home/hzheng/clearml/alcf_clearml_evaluation/tests/pipeline/globus_compute_bridge/tasks/globus_script.sh",
        script_args=None,
        binary="/bin/bash",
        tags=["globus-bridge"],  # consumed by bridge_worker.py in bridge mode
    )

    user_props = {
        "account": "datascience",
        "queue": "workq",
        "num_nodes": 2,
        "cores_per_node": 64,
        "walltime": "00:10:00",
        "filesystems": "eagle:home",
        "max_blocks": 10,
        "min_blocks": 0,
        "init_blocks": 0,
    }

    submit_task.set_user_properties(
        **user_props,
    )

    postprocess_task = Task.create(
        project_name="AmSC/pipeline-globus-bridge",
        task_name="globus-postprocess-v2",
        task_type=Task.TaskTypes.testing,
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory="./tests/pipeline/globus_compute_bridge",
        script="./tasks/postprocess_results.py",
        binary="python",
        argparse_args=[("--expected-min-output", "1")],
    )

    pipe = PipelineController(
        name="globus-compute-bridge-pipeline",
        project="amsc/pipeline-globus-bridge",
        version="0.1",
        add_pipeline_tags=True,
    )

    pipe.add_step(
        name="globus_submit",
        base_task_id=submit_task.id,
        execution_queue='crux-services',
    )

    pipe.add_step(
        name="postprocess",
        base_task_id=postprocess_task.id,
        execution_queue='crux-services',
        parents=["globus_submit"],
    )

    pipe.start(queue='crux-services')
    print(f"Pipeline started: {pipe.id}")


if __name__ == "__main__":
    main()
