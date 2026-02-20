import os
import shlex

from clearml import PipelineController, Task
from globus_compute_launcher import GlobusComputeLauncher

PROJECT = "amsc/pipeline-globus-bridge"
QUEUE = os.getenv("CLEARML_CONTROLLER_QUEUE", "crux-services")
ENDPOINT_ID = os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", "fad4d968-8c9a-45ce-9fb4-60a9ab90be60")
LOCAL_WRAPPER_WORKDIR = "./tests/pipeline/globus_compute_bridge"


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
    account = _env_optional("GLOBUS_ACCOUNT", "datascience")
    queue_name = _env_optional("GLOBUS_QUEUE", "by-gpu")
    partition = _env_optional("GLOBUS_PARTITION")
    walltime = _env_optional("GLOBUS_WALLTIME", "0:10:00")
    num_nodes = int(_env_optional("GLOBUS_NUM_NODES", "1") or "1")
    cores_per_node = (
        int(_env_optional("GLOBUS_CORES_PER_NODE"))
        if _env_optional("GLOBUS_CORES_PER_NODE")
        else None
    )

    submit_task = launcher.create(
        project_name=PROJECT,
        task_name="globus-submit-wrapper-v5",
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory=LOCAL_WRAPPER_WORKDIR,
        task_type=Task.TaskTypes.data_processing,
        launcher_working_directory=LOCAL_WRAPPER_WORKDIR,
        script_working_directory=_env_optional("GLOBUS_SCRIPT_WORKING_DIRECTORY"),
        endpoint_id=ENDPOINT_ID,
        input_value=7,
        poll_interval=5,
        timeout_sec=900,
        script=os.getenv("GLOBUS_SCRIPT", "/home/hzheng/clearml/alcf_clearml_evaluation/tests/pipeline/globus_compute_bridge/tasks/globus_script.sh"),
        script_args=shlex.split(os.getenv("GLOBUS_SCRIPT_ARGS", "")),
        binary=os.getenv("GLOBUS_BINARY", "/bin/bash"),
        account=account,
        queue=queue_name,
        partition=partition,
        num_nodes=num_nodes,
        cores_per_node=cores_per_node,
        walltime=walltime,
        tags=["globus-bridge"],  # consumed by bridge_worker.py in bridge mode
    )
    submit_task.set_user_properties(
        account=account,
        queue=queue_name,
        partition=partition,
        num_nodes=num_nodes,
        cores_per_node=cores_per_node,
        walltime=walltime,
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
