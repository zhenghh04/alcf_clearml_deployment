from clearml import Task, PipelineController

# 1) Create base tasks (only once)
prepare_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="prepare-data",
    task_type=Task.TaskTypes.data_processing,
    repo="https://github.com/zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/multi_facilities",
    script="./tasks/prepare_data.sh",
    binary="/bin/bash",
)


transfer_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="transfer-data",
    task_type=Task.TaskTypes.data_processing,
    repo="https://github.com/zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/multi_facilities",
    script="./tasks/globus_transfer.sh",
    binary="/bin/bash",
)

train_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="train-model",
    task_type=Task.TaskTypes.training,
    repo="https://github.com/zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/multi_facilities",
    script="./tasks/train.sh",
    binary="/bin/bash",
)

train_task.set_user_properties(
    walltime="0:10:00",
    num_nodes=1,
    account="datascience",
    queue="debug",
)

eval_task = Task.create(
    project_name="amsc/pipeline-demo",
    task_name="evaluate-model",
    task_type=Task.TaskTypes.testing,
    repo="https://github.com/zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/multi_facilities",
    script="./tasks/evaluate.sh",
    binary="/bin/bash",
)

eval_task.set_user_properties(
    walltime="0:10:00",
    num_nodes=1,
    account="datascience",
    queue = "debug",
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
    execution_queue="crux-login",
)

pipe.add_step(
    name="transfer_data",
    base_task_id=transfer_task.id,
    execution_queue="crux-login",
    parents=["prepare_data"],
)

pipe.add_step(
    name="train",
    base_task_id=train_task.id,
    execution_queue="aurora",
    parents=["transfer_data"],
)
pipe.add_step(
    name="evaluate",
    base_task_id=eval_task.id,
    execution_queue="aurora",
    parents=["train"],
)

pipe.start(queue="crux-login")
print("Pipeline started:", pipe.id)