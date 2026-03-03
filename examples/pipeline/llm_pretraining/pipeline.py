from clearml import PipelineController, Task
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
DATA_ROOT = "/eagle/AuroraGPT/hzheng/datasets"
DATA_ROOT_AURORA = "/flare/AuroraGPT/hzheng/datasets"
DOLMA_REPO = "allenai/dolma"
DOLMA_REVISION = "main"
DOLMA_VERSION = "v1_7"
DOLMA_DATASET_DIR = f"{DATA_ROOT}/{DOLMA_REPO}/{DOLMA_VERSION}"
DOLMA_FUSED_DIR = f"{DOLMA_DATASET_DIR}-fused"
DOLMA_TOKENIZED_DIR = f"{DOLMA_FUSED_DIR}-tok"
DOLMA_TOKENIZED_DIR_AURORA = f"{DATA_ROOT_AURORA}/{DOLMA_REPO}/{DOLMA_VERSION}-fused-tok"
TOKENIZER_MODEL = "/eagle/AuroraGPT/hzheng/gemma-7b"
CHECKPOINT_DIR = f"{DATA_ROOT_AURORA}/checkpoints/auroragpt-7b"

download_dolma_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="download-dolma-v1.7",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory="./examples/pipeline/llm_pretraining",
    script="./tasks/download_dolma_v1.7.sh",
    binary="/bin/bash",
    argparse_args=[
        ("data-root", DATA_ROOT),
        ("repo-id", DOLMA_REPO),
        ("revision", DOLMA_REVISION),
        ("dolma-version", DOLMA_VERSION),
        ("num-workers", "8"),
    ],
)

fuse_dolma_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="fuse-dolma-v1.7-files",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory="./examples/pipeline/llm_pretraining",
    script="./tasks/fuse_files.sh",
    binary="/bin/bash",
    argparse_args=[
        ("input-dir", DOLMA_DATASET_DIR),
        ("output-dir", DOLMA_FUSED_DIR),
    ],
)

tokenize_dolma_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="tokenize-dolma-v1.7-dataset",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory="./examples/pipeline/llm_pretraining",
    script="./tasks/tokenization.sh",
    binary="/bin/bash",
    argparse_args=[
        ("input-dir", DOLMA_FUSED_DIR),
        ("output-dir", DOLMA_TOKENIZED_DIR),
        ("tokenizer-model", TOKENIZER_MODEL),
    ],
)

train_auroragpt_7b_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="train-auroragpt-7b",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory="./examples/pipeline/llm_pretraining",
    script="./tasks/train_auroragpt_7b.sh",
    binary="/bin/bash",
    argparse_args=[
        ("data-paths", DOLMA_TOKENIZED_DIR_AURORA),
        ("output-dir", CHECKPOINT_DIR),
        ("dry-run", "1"),
    ],
)

train_auroragpt_7b_task.set_user_properties(
    walltime="02:00:00",
    num_nodes=1,
    account="datascience",
    queue="debug",
)

transfer_to_aurora_task = Task.create(
    project_name="amsc/llm-pretraining",
    task_name="transfer-dolma-tokenized-to-aurora",
    task_type=Task.TaskTypes.data_processing,
    repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
    branch="main",
    working_directory="./examples/pipeline/llm_pretraining",
    script="./tasks/transfer_tokenized_to_aurora.sh",
    binary="/bin/bash",
    argparse_args=[
        ("src-path", DOLMA_TOKENIZED_DIR),
        ("dst-path", DOLMA_TOKENIZED_DIR_AURORA),
        ("recursive", "1"),
        ("poll-interval", "30"),
    ],
)

pipe = PipelineController(
    name="llm-pretraining-pipeline",
    project="amsc/llm-pretraining",
    version="0.1",
    packages=["clearml>=2.1.3"],
    docker="python:3.13-slim",
)


pipe.add_step(
    name="download_dolma",
    base_task_id=download_dolma_task.id,
    execution_queue="crux-services",
)

pipe.add_step(
    name="fuse_dolma_files",
    base_task_id=fuse_dolma_task.id,
    execution_queue="crux",
    parents=["download_dolma"],
)

pipe.add_step(
    name="tokenize_dolma",
    base_task_id=tokenize_dolma_task.id,
    execution_queue="crux",
    parents=["fuse_dolma_files"],
)

pipe.add_step(
    name="transfer_tokenized_to_aurora",
    base_task_id=transfer_to_aurora_task.id,
    execution_queue="crux-services",
    parents=["tokenize_dolma"],
)

pipe.add_step(
    name="train_auroragpt_7b",
    base_task_id=train_auroragpt_7b_task.id,
    execution_queue="aurora",
    parents=["transfer_tokenized_to_aurora"],
)

pipe.start(queue="crux-services")
print("Pipeline started:", pipe.id)
