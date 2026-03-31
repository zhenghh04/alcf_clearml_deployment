import sys
from pathlib import Path

from clearml import Task

REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_globus_bridge import GlobusDataMover
from clearml_iri_bridge import IRILauncher, build_job_payload


PROJECT_NAME = "AmSC/pipeline-iri-bridge"
TRANSFER_TASK_NAME = "stage-script-with-globus"
IRI_TASK_NAME = "submit-iri-job-after-stage-in"
TRANSFER_QUEUE = "services"
IRI_QUEUE = "crux-services"

SRC_ENDPOINT = "YOUR_LOCAL_ENDPOINT"
DST_ENDPOINT = "YOUR_REMOTE_ENDPOINT"
SRC_PATH = "/path/on/local/machine/job.sh"
DST_PATH = "/home/hzheng/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/job.sh"


def main() -> int:
    mover = GlobusDataMover()
    transfer_task = mover.create(
        project_name=PROJECT_NAME,
        task_name=TRANSFER_TASK_NAME,
        src_endpoint=SRC_ENDPOINT,
        dst_endpoint=DST_ENDPOINT,
        src_path=SRC_PATH,
        dst_path=DST_PATH,
        recursive=False,
        tags=["globus-transfer", "iri-bridge"],
    )
    Task.enqueue(transfer_task, queue_name=TRANSFER_QUEUE)

    launcher = IRILauncher()
    job_payload = build_job_payload(
        scheduler="pbs",
        name="clearml-iri-job",
        directory="/eagle/datascience/hzheng/",
        stdout_path="/eagle/datascience/hzheng/iri.out",
        stderr_path="/eagle/datascience/hzheng/iri.err",
        account="AmSC_Demos",
        queue_name="debug",
        duration=300,
        custom_attributes={"filesystems": "home:eagle"},
        script_path=DST_PATH,
    )
    submit_task = launcher.create(
        project_name=PROJECT_NAME,
        task_name=IRI_TASK_NAME,
        task_type=Task.TaskTypes.data_processing,
        repo="https://github.com/zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        working_directory=".",
        facility="alcf",
        system="polaris",
        job_payload=job_payload,
        tags=["iri-bridge", "stage-in"],
    )

    print(f"Enqueued transfer task: {transfer_task.id} on queue {TRANSFER_QUEUE}")
    try:
        print(f"Transfer log URL: {transfer_task.get_output_log_web_page()}")
    except Exception:
        pass
    print(f"Created IRI task: {submit_task.id}")
    try:
        print(f"IRI log URL: {submit_task.get_output_log_web_page()}")
    except Exception:
        pass
    print(
        "Enqueue the IRI task after the transfer task completes so the remote script "
        "is present at the destination path."
    )
    print(f"Suggested enqueue command: Task.enqueue(submit_task, queue_name={IRI_QUEUE!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
