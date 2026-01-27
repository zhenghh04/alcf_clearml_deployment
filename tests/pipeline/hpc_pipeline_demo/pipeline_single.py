from clearml import Task, PipelineController

# 1) Create base tasks (only once)
prepare_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="prepare-data",
    task_type=Task.TaskTypes.data_processing,
    script="tests/pipeline/hpc_pipeline_demo/tasks/prepare_data.sh",
    binary="/bin/bash",
)
train_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="train-model",
    task_type=Task.TaskTypes.training,
    script="tests/pipeline/hpc_pipeline_demo/tasks/train.sh",
    binary="/bin/bash",
)
eval_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="evaluate-model",
    task_type=Task.TaskTypes.testing,
    script="tests/pipeline/hpc_pipeline_demo/tasks/evaluate.sh",
    binary="/bin/bash",
)

# 2) Build pipeline using task IDs
pipe = PipelineController(
    name="example-hpc-pipeline",
    project="amsc/pipeline-demo",
    version="1.1",
)

pipe.add_step(
    name="prepare_data",
    base_task_id=prepare_task.id,
    execution_queue="sirius-login",
)
pipe.add_step(
    name="train",
    base_task_id=train_task.id,
    execution_queue="sirius-login",
    parents=["prepare_data"],
)
pipe.add_step(
    name="evaluate",
    base_task_id=eval_task.id,
    execution_queue="sirius-login",
    parents=["train"],
)

pipe.start()
print("Pipeline started:", pipe.id)
