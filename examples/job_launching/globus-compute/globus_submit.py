import sys
from pathlib import Path

from clearml import Task

REPO_ROOT = Path(__file__).resolve().parents[3]
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_globus_bridge.globus_compute_launcher import GlobusComputeLauncher


def main() -> int:
    launcher = GlobusComputeLauncher()
    submit_task = launcher.create(
        project_name="AmSC/globus-job-launching",
        task_name="test-services",
        task_type=Task.TaskTypes.training,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        working_directory="./examples/job_launching/globus-compute",
        endpoint_id=None,
        endpoint_name="crux-compute",
        script="/home/hzheng/clearml/alcf_clearml_deployment/examples/pipeline/globus_compute_bridge/tasks/globus_script.sh",
        binary="/bin/bash",
        clone_repo=False,
        poll_interval=5,
        timeout_sec=900,
        artifact_path="globus_result.json",
        tags=["globus-bridge", "job-launching"],
    )



    Task.enqueue(submit_task, queue_name="services")
    print(f"Enqueued task: {submit_task.id} on queue services")
    print(f"Log URL: {submit_task.get_output_log_web_page()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
