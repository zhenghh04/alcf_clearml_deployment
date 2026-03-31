import sys
import os
from pathlib import Path

from clearml import Task

REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_iri_bridge import IRILauncher, build_job_payload


def main() -> int:
    launcher = IRILauncher()
    job_payload = build_job_payload(
        scheduler="pbs",
        name="clearml-iri-job",
        directory="/lus/eagle/projects/datascience/hzheng/",
        stdout_path="/lus/eagle/projects/datascience/hzheng/iri.out",
        stderr_path="/lus/eagle/projects/datascience/hzheng/iri.err",
        account="AmSC_Demos",
        queue_name="debug",
        duration=300,
        custom_attributes={"filesystems": "home:eagle"},
        script_path="/home/hzheng/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/job.sh",
    )
    submit_task = launcher.create(
        project_name="AmSC/pipeline-iri-bridge",
        task_name="submit-iri-job",
        task_type=Task.TaskTypes.data_processing,
        repo="https://github.com/zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        working_directory=".",
        facility="alcf",
        system="polaris",
        job_payload=job_payload,
        tags=["iri-bridge"],
    )

    Task.enqueue(submit_task, queue_name="crux-services")
    print(f"Enqueued task: {submit_task.id} on queue crux-services")
    try:
        print(f"ClearML results page: {submit_task.get_output_log_web_page()}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
