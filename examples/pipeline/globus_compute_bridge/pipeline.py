import os
import subprocess
import sys
from pathlib import Path

os.environ["CLEARML_FORCE_NO_REMOTE"] = "1"
os.environ.pop("CLEARML_DEFAULT_QUEUE", None)

from clearml import PipelineController, Task

# Ensure agent-side execution imports clearml_globus_bridge from this repo checkout.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_globus_bridge.globus_compute_launcher import GlobusComputeLauncher

def main() -> None:
    controller_task = Task.init(
        project_name="AmSC/pipeline-globus-compute-bridge",
        task_name="globus-compute-bridge-controller",
        task_type=Task.TaskTypes.controller,
    )

    launcher = GlobusComputeLauncher()
    submit_task = launcher.create(
        project_name="AmSC/pipeline-globus-compute-bridge",
        task_name="globus-compute-3",
        task_type=Task.TaskTypes.data_processing,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        working_directory="./examples/pipeline/globus_compute_bridge",
        endpoint_name="crux-compute",
        script="/home/hzheng/clearml/alcf_clearml_deployment/examples/pipeline/globus_compute_bridge/tasks/globus_script.sh",
        binary="/bin/bash",
        clone_repo=False,
        tags=["globus-bridge"],
    )

    submit_task.set_user_properties(
        account="datascience",
        queue="workq",
        num_nodes=2,
        cores_per_node=64,
        walltime="00:10:00",
        filesystems="eagle:home",
        max_blocks=10,
        min_blocks=0,
        init_blocks=0,
    )

    postprocess_task = Task.create(
        project_name="AmSC/pipeline-globus-compute-bridge",
        task_name="globus-postprocess",
        task_type=Task.TaskTypes.testing,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        working_directory="./examples/pipeline/globus_compute_bridge",
        script="./tasks/postprocess_results.py",
        binary="python",
        argparse_args=[("--expected-min-output", "1")],
    )

    pipe = PipelineController(
        name="globus-compute-bridge-pipeline",
        project="AmSC/pipeline-globus-compute-bridge",
        version="0.1",
        add_pipeline_tags=True,
    )
    pipe.add_step(
        name="globus_compute_on_crux",
        base_task_id=submit_task.id,
        execution_queue="services",
    )
    pipe.add_step(
        name="postprocess",
        base_task_id=postprocess_task.id,
        execution_queue="crux-services",
        parents=["globus_compute_on_crux"],
    )

    pipe.start(queue="services")
    print(f"Controller task id: {controller_task.id}")
    print(f"Submit task id: {submit_task.id}")
    print(f"Postprocess task id: {postprocess_task.id}")
    print(f"Pipeline started: {pipe.id}")


if __name__ == "__main__":
    main()
