from clearml import PipelineController, Task

MATH_DATASET_DIR = "/eagle/AuroraGPT/hzheng/NVIDIA/Nemotron-Math-v2"
CODE_DATASET_DIR = "/eagle/AuroraGPT/hzheng/NVIDIA/Nemotron-Pretraining-Code-v2"
MATH_FUSED_DIR = "/eagle/AuroraGPT/hzheng/NVIDIA/Nemotron-Math-v2-fused"
CODE_FUSED_DIR = "/eagle/AuroraGPT/hzheng/NVIDIA/Nemotron-Pretraining-Code-v2-fused"
MATH_TOKENIZED_DIR = "/eagle/AuroraGPT/hzheng//NVIDIA/Nemotron-Math-v2-fused-tok"
CODE_TOKENIZED_DIR = "/eagle/AuroraGPT/hzheng/NVIDIA/Nemotron-Pretraining-Code-v2-fused-tok"
TOKENIZER_MODEL = "/eagle/AuroraGPT/hzheng/gemma-7b"


download_math_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="download-nvidia-math",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/download_nvidia_math_code.sh",
    binary="/bin/bash",
)
download_math_task.set_environment(
    {
        "DOWNLOAD_MODE": "math",
    }
)

download_code_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="download-nvidia-code",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/download_nvidia_math_code.sh",
    binary="/bin/bash",
)
download_code_task.set_environment(
    {
        "DOWNLOAD_MODE": "code",
    }
)

check_code_access_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="check-code-access",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/check_hf_access.py",
    binary="python",
)
check_code_access_task.set_environment(
    {
        "HF_DATASET": "nvidia/Nemotron-Pretraining-Code-v2",
    }
)

fuse_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="fuse-small-files",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/fuse_files.sh",
    binary="/bin/bash",
)

fuse_math_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="fuse-math-files",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/fuse_files.sh",
    binary="/bin/bash",
)
fuse_math_task.set_environment(
    {
        "FUSE_INPUT_DIR": MATH_DATASET_DIR,
        "FUSE_OUTPUT_DIR": MATH_FUSED_DIR,
    }
)

fuse_code_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="fuse-code-files",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/fuse_files.sh",
    binary="/bin/bash",
)
fuse_code_task.set_environment(
    {
        "FUSE_INPUT_DIR": CODE_DATASET_DIR,
        "FUSE_OUTPUT_DIR": CODE_FUSED_DIR,
    }
)

tokenize_math_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="tokenize-math-dataset",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/tokenization.sh",
    binary="/bin/bash",
)
tokenize_math_task.set_environment(
    {
        "TOKEN_INPUT_DIR": MATH_FUSED_DIR,
        "TOKEN_OUTPUT_DIR": MATH_TOKENIZED_DIR,
        "TOKEN_TOKENIZER_MODEL": TOKENIZER_MODEL,
    }
)

tokenize_code_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="tokenize-code-dataset",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    working_directory="./tests/pipeline/llm_pretraining",
    script="./tasks/tokenization.sh",
    binary="/bin/bash",
)
tokenize_code_task.set_environment(
    {
        "TOKEN_INPUT_DIR": CODE_FUSED_DIR,
        "TOKEN_OUTPUT_DIR": CODE_TOKENIZED_DIR,
        "TOKEN_TOKENIZER_MODEL": TOKENIZER_MODEL,
    }
)

pipe = PipelineController(
    name="llm-pretraining-pipeline",
    project="amsc/llm-pretraining",
    version="0.1",
    packages=["clearml>=2.1.3"],
    docker="python:3.13-slim",
)

pipe.add_step(
    name="download_math",
    base_task_id=download_math_task.id,
    execution_queue="crux-services",
)

pipe.add_step(
    name="download_code",
    base_task_id=download_code_task.id,
    execution_queue="crux-services",
    parents=["check_code_access"],
)

pipe.add_step(
    name="check_code_access",
    base_task_id=check_code_access_task.id,
    execution_queue="crux-services",
)

pipe.add_step(
    name="fuse_math_files",
    base_task_id=fuse_math_task.id,
    execution_queue="crux",
    parents=["download_math"],
)

pipe.add_step(
    name="fuse_code_files",
    base_task_id=fuse_code_task.id,
    execution_queue="crux",
    parents=["download_code"],
)

pipe.add_step(
    name="tokenize_math",
    base_task_id=tokenize_math_task.id,
    execution_queue="crux",
    parents=["fuse_math_files"],
)

pipe.add_step(
    name="tokenize_code",
    base_task_id=tokenize_code_task.id,
    execution_queue="crux",
    parents=["fuse_code_files"],
)

pipe.start(queue="crux-services")
print("Pipeline started:", pipe.id)
