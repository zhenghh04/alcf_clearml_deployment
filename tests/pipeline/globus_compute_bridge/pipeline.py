import os
import shlex

from clearml import PipelineController, Task
from clearml_globus_bridge.globus_compute_launcher import GlobusComputeLauncher

PROJECT = "amsc/pipeline-globus-bridge"
QUEUE = os.getenv("CLEARML_CONTROLLER_QUEUE", "crux-services")
ENDPOINT_ID = os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", "66786535-12ec-463d-9d42-72f03d6aac41")
LOCAL_WRAPPER_WORKDIR = "./tests/pipeline/globus_compute_bridge"

# Scheduler/resource settings are intentionally configured in-code
# (not via environment variables) to keep runs reproducible.
SCHEDULER_SETTINGS = {
    "account": "datascience",
    "queue": "debug",
    "partition": None,
    "num_nodes": 1,
    "cores_per_node": None,
    "walltime": "0:10:00",
}

def _env_optional(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    normalized = value.strip()
    if normalized.lower() in {"", "none", "null"}:
        return None
    return normalized


def main() -> None:
    if not ENDPOINT_ID.strip():
        raise ValueError("GLOBUS_COMPUTE_ENDPOINT_ID must be set to a valid endpoint UUID.")

    launcher = GlobusComputeLauncher()
    account = SCHEDULER_SETTINGS["account"]
    queue_name = SCHEDULER_SETTINGS["queue"]
    partition = SCHEDULER_SETTINGS["partition"]
    walltime = SCHEDULER_SETTINGS["walltime"]
    num_nodes = SCHEDULER_SETTINGS["num_nodes"]
    cores_per_node = SCHEDULER_SETTINGS["cores_per_node"]

    submit_task = launcher.create(
        project_name=PROJECT,
        task_name="globus-submit-wrapper-v7",
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory=LOCAL_WRAPPER_WORKDIR,
        task_type=Task.TaskTypes.data_processing,
        # Run launcher task from repo root so module mode + `packages=["-e ."]` works.
        launcher_working_directory=".",
        script_working_directory=_env_optional("GLOBUS_SCRIPT_WORKING_DIRECTORY"),
        endpoint_id=ENDPOINT_ID,
        script=os.getenv("GLOBUS_SCRIPT", "/home/hzheng/clearml/alcf_clearml_evaluation/tests/pipeline/globus_compute_bridge/tasks/globus_script.sh"),
        script_args=shlex.split(os.getenv("GLOBUS_SCRIPT_ARGS", "")),
        binary=os.getenv("GLOBUS_BINARY", "/bin/bash"),
        tags=["globus-bridge"],  # consumed by bridge_worker.py in bridge mode
    )
    user_props = {
        "account": account,
        "queue": queue_name,
        "partition": partition,
        "num_nodes": num_nodes,
        "cores_per_node": cores_per_node,
        "walltime": walltime,
    }

    submit_task.set_user_properties(
        **user_props,
    )

    postprocess_task = Task.create(
        project_name=PROJECT,
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
        project=PROJECT,
        version="0.1",
        add_pipeline_tags=True,
    )

    pipe.add_step(
        name="globus_submit",
        base_task_id=submit_task.id,
        execution_queue=QUEUE,
    )

    pipe.add_step(
        name="postprocess",
        base_task_id=postprocess_task.id,
        execution_queue=QUEUE,
        parents=["globus_submit"],
    )

    pipe.start(queue=QUEUE)
    print(f"Pipeline started: {pipe.id}")


if __name__ == "__main__":
    main()
