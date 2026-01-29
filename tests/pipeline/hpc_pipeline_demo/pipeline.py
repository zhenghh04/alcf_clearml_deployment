from clearml import Task, PipelineController

# 1) Create base tasks (only once)
prepare_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="prepare-data",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/hpc_pipeline_demo",
    script="./tasks/prepare_data.sh",
    binary="/bin/bash",
)

train_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="train-model",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/hpc_pipeline_demo",
    script="./tasks/train.sh",
    binary="/bin/bash",
)
train_task.set_user_properties(
    walltime="0:10:00",
    num_nodes=1,
    account="datascience",
    queue="by-gpu",
)

eval_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="evaluate-model",
    task_type=Task.TaskTypes.testing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/hpc_pipeline_demo",
    script="./tasks/evaluate.sh",
    binary="/bin/bash",
)

eval_task.set_user_properties(
    walltime="0:10:00",
    num_nodes=1,
    account="datascience",
    queue = "by-gpu",
)

# 2) Build pipeline using task IDs
pipe = PipelineController(
    name="example-hpc-pipeline",
    project="amsc/pipeline-demo",
    version="1.1",
    packages = ["clearml>=2.1.3"],
    docker = "python:3.13-slim",

)

pipe.add_step(
    name="prepare_data",
    base_task_id=prepare_task.id,
    execution_queue="sophia-login",
)
pipe.add_step(
    name="train",
    base_task_id=train_task.id,
    execution_queue="sophia-login",
    parents=["prepare_data"],
)
pipe.add_step(
    name="evaluate",
    base_task_id=eval_task.id,
    execution_queue="sophia-login",
    parents=["train"],
)

pipe.start()
print("Pipeline started:", pipe.id)