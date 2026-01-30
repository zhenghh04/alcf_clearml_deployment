from clearml import PipelineController, Task


# 1) Create base tasks (only once)
prepare_task = Task.create(
    project_name="amsc/ensemble-demo",
    task_name="prepare-data",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/ensemble_pipeline",
    script="./tasks/prepare.sh",
    binary="/bin/bash",
)

train_a_task = Task.create(
    project_name="amsc/ensemble-demo",
    task_name="train-model-a",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/ensemble_pipeline",
    script="./tasks/train_a.sh",
    binary="/bin/bash",
)

train_b_task = Task.create(
    project_name="amsc/ensemble-demo",
    task_name="train-model-b",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/ensemble_pipeline",
    script="./tasks/train_b.sh",
    binary="/bin/bash",
)

ensemble_eval_task = Task.create(
    project_name="amsc/ensemble-demo",
    task_name="ensemble-evaluate",
    task_type=Task.TaskTypes.testing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/ensemble_pipeline",
    script="./tasks/ensemble_eval.sh",
    binary="/bin/bash",
)

# 2) Build pipeline using task IDs
pipe = PipelineController(
    name="ensemble-parallel-pipeline",
    project="amsc/ensemble-demo",
    version="1.0",
    packages=["clearml>=2.1.3"],
    docker="python:3.13-slim",
)

pipe.add_step(
    name="prepare_data",
    base_task_id=prepare_task.id,
    execution_queue="crux-services",
)

# Parallel training steps (same parent, no dependency between them)
pipe.add_step(
    name="train_model_a",
    base_task_id=train_a_task.id,
    execution_queue="crux",
    parents=["prepare_data"],
)
pipe.add_step(
    name="train_model_b",
    base_task_id=train_b_task.id,
    execution_queue="crux",
    parents=["prepare_data"],
)

# Ensemble evaluation depends on both training steps
pipe.add_step(
    name="ensemble_evaluate",
    base_task_id=ensemble_eval_task.id,
    execution_queue="crux",
    parents=["train_model_a", "train_model_b"],
)

pipe.start(queue="crux-services")
print("Pipeline started:", pipe.id)