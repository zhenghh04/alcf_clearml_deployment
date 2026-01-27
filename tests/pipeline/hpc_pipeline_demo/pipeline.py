from clearml import PipelineController
from clearml import Task


def main():
    pipe = PipelineController(
        name="example-hpc-pipeline",
        project="amsc/pipeline-demo",
        version="1.0",
        add_pipeline_tags=True,
        docker=None,
    )

    # Optional: default queue (fallback)
    pipe.set_default_execution_queue("sirius-login")
    

    # ---- Step 1: Prepare data ----
    pipe.add_step(
        name="prepare_data",
        base_task_project="amsc/pipeline-demo",
        base_task_name="prepare-data",
        execution_queue="sophia-login",
    )

    # ---- Step 1b: Move dataset ----
    #pipe.add_step(
    #    name="move_dataset",
    #    base_task_project="amsc/pipeline-demo",
    #    base_task_name="move-dataset",
    #    execution_queue="sophia-login",
    #    parents=["prepare_data"],
    #)

    # ---- Step 2: Train ----
    pipe.add_step(
        name="train",
        base_task_project="amsc/pipeline-demo",
        base_task_name="train-model",
        execution_queue="sophia-login",
        parents=["prepare_data"],
    )

    # ---- Step 3: Evaluate ----
    pipe.add_step(
        name="evaluate",
        base_task_project="amsc/pipeline-demo",
        base_task_name="evaluate-model",
        execution_queue="sophia-login",
        parents=["train"],
    )

    # Start execution
    pipe.start()

    print(f"Pipeline started: {pipe.id}")


if __name__ == "__main__":
    main()
