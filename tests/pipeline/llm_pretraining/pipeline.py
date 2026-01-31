from clearml import PipelineController, Task


download_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="download-nvidia-math-code",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/download_nvidia_math_code.sh",
    binary="/bin/bash",
)

pipe = PipelineController(
    name="llm-pretraining-pipeline",
    project="amsc/llm-pretraining",
    version="0.1",
    packages=["clearml>=2.1.3"],
    docker="python:3.13-slim",
)

pipe.add_step(
    name="download_datasets",
    base_task_id=download_task.id,
    execution_queue="crux-services",
)

pipe.start(queue="crux-services")
print("Pipeline started:", pipe.id)
