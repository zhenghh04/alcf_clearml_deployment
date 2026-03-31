import sys
from pathlib import Path

from clearml import PipelineController, Task

REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_globus_bridge import GlobusDataMover
from clearml_iri_bridge import IRILauncher, build_job_payload


SRC_ENDPOINT = "zion"
DST_ENDPOINT = "eagle"
SRC_PATH = "/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/job.sh"
DST_PATH = "/datascience/hzheng/job.sh"


def main() -> int:
    controller_task = Task.init(
        project_name="AmSC/pipeline-iri-bridge",
        task_name="iri-stage-with-globus-pipeline",
        task_type=Task.TaskTypes.controller,
    )

    mover = GlobusDataMover()
    transfer_task = mover.create(
        project_name="AmSC/pipeline-iri-bridge",
        task_name="stage-script-with-globus",
        src_endpoint=SRC_ENDPOINT,
        dst_endpoint=DST_ENDPOINT,
        src_path=SRC_PATH,
        dst_path=DST_PATH,
        recursive=False,
        tags=["globus-transfer", "iri-bridge", "pipeline"],
    )

    launcher = IRILauncher()
    job_payload = build_job_payload(
        scheduler="pbs",
        name="clearml-iri-job-stage",
        directory="/lus/eagle/projects/datascience/hzheng/",
        stdout_path="/lus/eagle/projects/datascience/hzheng/iri.out",
        stderr_path="/lus/eagle/projects/datascience/hzheng/iri.err",
        account="AmSC_Demos",
        queue_name="debug",
        duration=300,
        custom_attributes={"filesystems": "home:eagle"},
        script_path="/lus/eagle/projects/datascience/hzheng/job.sh",
    )
    submit_task = launcher.create(
        project_name="AmSC/pipeline-iri-bridge",
        task_name="submit-iri-job-after-stage-in",
        task_type=Task.TaskTypes.data_processing,
        working_directory=".",
        facility="alcf",
        system="polaris",
        job_payload=job_payload,
        tags=["iri-bridge", "stage-in", "pipeline"],
    )

    pipe = PipelineController(
        name="iri-stage-with-globus-pipeline",
        project="AmSC/pipeline-iri-bridge",
        version="0.1",
        add_pipeline_tags=True,
    )
    pipe.add_step(
        name="stage_in_with_globus",
        base_task_id=transfer_task.id,
        execution_queue="crux-services",
    )
    pipe.add_step(
        name="submit_iri_job",
        base_task_id=submit_task.id,
        execution_queue="crux-services",
        parents=["stage_in_with_globus"],
    )

    pipe.start(queue="crux-services")

    print(f"Controller task id: {controller_task.id}")
    print(f"Transfer task id: {transfer_task.id}")
    print(f"IRI task id: {submit_task.id}")
    print(f"Pipeline started: {pipe.id}")
    try:
        print(f"Pipeline log URL: {pipe.get_output_log_web_page()}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
