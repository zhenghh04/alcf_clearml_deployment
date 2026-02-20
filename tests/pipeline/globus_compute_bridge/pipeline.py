import os

from clearml import PipelineController, Task

PROJECT = "amsc/pipeline-globus-bridge"
QUEUE = os.getenv("CLEARML_CONTROLLER_QUEUE", "crux-services")
#ENDPOINT_ID = os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", "REPLACE_WITH_ENDPOINT_ID")
ENDPOINT_ID = "fad4d968-8c9a-45ce-9fb4-60a9ab90be60"

def main() -> None:
    submit_task = Task.create(
        project_name=PROJECT,
        task_name="globus-submit-wrapper-v2",
        task_type=Task.TaskTypes.data_processing,
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",
        working_directory="./tests/pipeline/globus_compute_bridge",
        script="./tasks/submit_globus_job.py",
        binary="python",
        argparse_args=[
            ("--endpoint-id", ENDPOINT_ID),
            ("--input-value", "7"),
            ("--poll-interval", "5"),
            ("--timeout-sec", "900"),
        ],
    )
    submit_task.set_parameters_as_dict(
        {
            "Args/endpoint-id": ENDPOINT_ID,
            "env:GLOBUS_COMPUTE_ENDPOINT_ID": ENDPOINT_ID,
        }
    )

    # Tag used by bridge_worker.py in bridge mode (optional).
    submit_task.set_tags(["globus-bridge"])  # no-op for direct wrapper mode

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
