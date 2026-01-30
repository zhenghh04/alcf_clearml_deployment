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
    script="./tasks/train_a.py",
    binary="python",
)

train_b_task = Task.create(
    project_name="amsc/ensemble-demo",
    task_name="train-model-b",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/ensemble_pipeline",
    script="./tasks/train_b.py",
    binary="python",
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
train_a_variants = [
    {"Args/learning_rate": 0.001, "Args/epochs": 10},
    {"Args/learning_rate": 0.001, "Args/epochs": 20},
    {"Args/learning_rate": 0.002, "Args/epochs": 10},
    {"Args/learning_rate": 0.002, "Args/epochs": 20},
    {"Args/learning_rate": 0.005, "Args/epochs": 10},
    {"Args/learning_rate": 0.005, "Args/epochs": 20},
    {"Args/learning_rate": 0.01, "Args/epochs": 10},
    {"Args/learning_rate": 0.01, "Args/epochs": 20},
]

train_b_variants = [
    {"Args/learning_rate": 0.001, "Args/epochs": 10},
    {"Args/learning_rate": 0.001, "Args/epochs": 20},
    {"Args/learning_rate": 0.002, "Args/epochs": 10},
    {"Args/learning_rate": 0.002, "Args/epochs": 20},
    {"Args/learning_rate": 0.005, "Args/epochs": 10},
    {"Args/learning_rate": 0.005, "Args/epochs": 20},
    {"Args/learning_rate": 0.01, "Args/epochs": 10},
    {"Args/learning_rate": 0.01, "Args/epochs": 20},
]

train_a_steps = []
train_b_steps = []
for idx, params in enumerate(train_a_variants, start=1):
    step_name = f"train_model_a_{idx}"
    pipe.add_step(
        name=step_name,
        base_task_id=train_a_task.id,
        execution_queue="crux",
        parents=["prepare_data"],
        parameter_override=params,
    )
    train_a_steps.append(step_name)

for idx, params in enumerate(train_b_variants, start=1):
    step_name = f"train_model_b_{idx}"
    pipe.add_step(
        name=step_name,
        base_task_id=train_b_task.id,
        execution_queue="crux",
        parents=["prepare_data"],
        parameter_override=params,
    )
    train_b_steps.append(step_name)

# Ensemble evaluation depends on both training steps
pipe.add_step(
    name="ensemble_evaluate",
    base_task_id=ensemble_eval_task.id,
    execution_queue="crux",
    parents=train_a_steps + train_b_steps,
)

pipe.start(queue="crux-services")
print("Pipeline started:", pipe.id)
