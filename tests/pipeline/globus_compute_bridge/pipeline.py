import os
import shlex

from clearml import PipelineController, Task
from globus_compute_launcher import GlobusComputeLauncher

PROJECT = "amsc/pipeline-globus-bridge"
QUEUE = os.getenv("CLEARML_CONTROLLER_QUEUE", "crux-services")
ENDPOINT_ID = os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", "fad4d968-8c9a-45ce-9fb4-60a9ab90be60")


def main() -> None:
    launcher = GlobusComputeLauncher()

    submit_task = launcher.create(
        project_name=PROJECT,
        task_name="globus-submit-wrapper-v5",
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory=os.getenv(
            "GLOBUS_WORKING_DIRECTORY", "./tests/pipeline/globus_compute_bridge"
        ),
        task_type=Task.TaskTypes.data_processing,
        launcher_working_directory="./tests/pipeline/globus_compute_bridge",
        endpoint_id=ENDPOINT_ID,
        input_value=7,
        poll_interval=5,
        timeout_sec=900,
        script="./tasks/globus_script.sh",
        script_args=shlex.split(os.getenv("GLOBUS_SCRIPT_ARGS", "")),
        binary=os.getenv("GLOBUS_BINARY", "/bin/bash"),
        tags=["globus-bridge"],  # consumed by bridge_worker.py in bridge mode
    )
    submit_task.set_user_properties(
        account=os.getenv("GLOBUS_ACCOUNT", "datascience"),
        queue=os.getenv("GLOBUS_QUEUE"),
        partition=os.getenv("GLOBUS_PARTITION"),
        num_nodes=int(os.getenv("GLOBUS_NUM_NODES", "1")),
        cores_per_node=(
            int(os.getenv("GLOBUS_CORES_PER_NODE"))
            if os.getenv("GLOBUS_CORES_PER_NODE")
            else None
        ),
        walltime=os.getenv("GLOBUS_WALLTIME"),
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
        name="submit_on_globus",
        base_task_id=submit_task.id,
        execution_queue=QUEUE,
    )

    pipe.add_step(
        name="postprocess",
        base_task_id=postprocess_task.id,
        execution_queue=QUEUE,
        parents=["submit_on_globus"],
    )

    pipe.start(queue=QUEUE)
    print(f"Pipeline started: {pipe.id}")


if __name__ == "__main__":
    main()
