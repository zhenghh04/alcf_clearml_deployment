#!/usr/bin/env bash
set -euo pipefail

DATA_PATHS="${TRAIN_DATA_PATHS:-/flare/AuroraGPT/hzheng/datasets/nvidia/Nemotron-Math-v2-fused-tok,/flare/AuroraGPT/hzheng/datasets/allenai/c4-fused-tok}"
OUTPUT_DIR="${TRAIN_OUTPUT_DIR:-/flare/AuroraGPT/hzheng/datasets/checkpoints/auroragpt-7b}"
MICRO_BATCH_SIZE="${TRAIN_MICRO_BATCH_SIZE:-1}"
GLOBAL_BATCH_SIZE="${TRAIN_GLOBAL_BATCH_SIZE:-128}"
SEQ_LENGTH="${TRAIN_SEQ_LENGTH:-4096}"
TRAIN_ITERS="${TRAIN_ITERS:-1000}"
LR="${TRAIN_LR:-3e-4}"
TENSOR_MODEL_PARALLEL_SIZE="${TRAIN_TENSOR_MODEL_PARALLEL_SIZE:-1}"
PIPELINE_MODEL_PARALLEL_SIZE="${TRAIN_PIPELINE_MODEL_PARALLEL_SIZE:-1}"
NUM_NODES="${TRAIN_NUM_NODES:-1}"
GPUS_PER_NODE="${TRAIN_GPUS_PER_NODE:-12}"
DRY_RUN="${TRAIN_DRY_RUN:-1}"

usage() {
  cat <<'USAGE'
Usage: train_auroragpt_7b.sh [options]

Options:
  --data-paths CSV         Comma-separated tokenized dataset paths
  --output-dir PATH        Checkpoint output directory
  --micro-batch-size N     Micro batch size per GPU (default: 1)
  --global-batch-size N    Global batch size (default: 128)
  --seq-length N           Sequence length (default: 4096)
  --train-iters N          Number of training iterations (default: 1000)
  --lr FLOAT               Learning rate (default: 3e-4)
  --tp N                   Tensor model parallel size (default: 1)
  --pp N                   Pipeline model parallel size (default: 1)
  --num-nodes N            Number of nodes (default: 1)
  --gpus-per-node N        Number of GPUs per node (default: 12)
  --dry-run 0|1            Print launch command without executing (default: 1)
  -h, --help               Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-paths)
      DATA_PATHS="$2"; shift 2 ;;
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --micro-batch-size)
      MICRO_BATCH_SIZE="$2"; shift 2 ;;
    --global-batch-size)
      GLOBAL_BATCH_SIZE="$2"; shift 2 ;;
    --seq-length)
      SEQ_LENGTH="$2"; shift 2 ;;
    --train-iters)
      TRAIN_ITERS="$2"; shift 2 ;;
    --lr)
      LR="$2"; shift 2 ;;
    --tp)
      TENSOR_MODEL_PARALLEL_SIZE="$2"; shift 2 ;;
    --pp)
      PIPELINE_MODEL_PARALLEL_SIZE="$2"; shift 2 ;;
    --num-nodes)
      NUM_NODES="$2"; shift 2 ;;
    --gpus-per-node)
      GPUS_PER_NODE="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"

WORLD_SIZE=$((NUM_NODES * GPUS_PER_NODE))

TRAIN_CMD="${AURORAGPT_TRAIN_CMD:-}"
if [[ -z "${TRAIN_CMD}" ]]; then
  TRAIN_CMD="deepspeed --num_nodes ${NUM_NODES} --num_gpus ${GPUS_PER_NODE} pretrain_gpt.py \
--data-path ${DATA_PATHS} \
--save ${OUTPUT_DIR} \
--load ${OUTPUT_DIR} \
--tensor-model-parallel-size ${TENSOR_MODEL_PARALLEL_SIZE} \
--pipeline-model-parallel-size ${PIPELINE_MODEL_PARALLEL_SIZE} \
--micro-batch-size ${MICRO_BATCH_SIZE} \
--global-batch-size ${GLOBAL_BATCH_SIZE} \
--seq-length ${SEQ_LENGTH} \
--train-iters ${TRAIN_ITERS} \
--lr ${LR}"
fi

echo "[train] world_size=${WORLD_SIZE} nodes=${NUM_NODES} gpus_per_node=${GPUS_PER_NODE}"
echo "[train] data_paths=${DATA_PATHS}"
echo "[train] output_dir=${OUTPUT_DIR}"
echo "[train] command=${TRAIN_CMD}"

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "[train] DRY_RUN=1, skipping execution."
  exit 0
fi

bash -lc "${TRAIN_CMD}"
echo "[train] Done"
