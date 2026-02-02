#!/usr/bin/env bash
set -euo pipefail
# set conda environment
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
source /eagle/AuroraGPT/hzheng/pyenvs/blendcorpus/bin/activate
INPUT_DIR="${TOKEN_INPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data-fused}"
OUTPUT_DIR="${TOKEN_OUTPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data-fused-tok}"
TOKENIZER_TYPE="${TOKEN_TOKENIZER_TYPE:-"HFTokenizer"}"
TOKENIZER_MODEL="${TOKEN_TOKENIZER_MODEL:-"/eagle/AuroraGPT/hzheng/gemma-7b/}"
NUM_WORKERS="${TOKEN_NUM_WORKERS:-16}"
PPN="${TOKEN_PPN:-4}"
DEPTH="${TOKEN_DEPTH:-16}"
APPEND_EOD="${TOKEN_APPEND_EOD:-1}"
NPROCS="${TOKEN_NPROCS:-}"

usage() {
  cat <<'USAGE'
Usage: tokenization.sh [options]

Options:
  --input-dir PATH        Input directory (default: /eagle/AuroraGPT/datasets/data-fused)
  --output-dir PATH       Output directory (default: /eagle/AuroraGPT/datasets/data-fused-tok)
  --tokenizer-type NAME   Tokenizer type (default: Llama2Tokenizer)
  --tokenizer-model PATH  Path to tokenizer model (required)
  --num-workers N         Intra-file worker processes (default: 16)
  --ppn N                 MPI ranks per node (default: 4)
  --depth N               CPU bind depth (default: 16)
  --nprocs N              Override total MPI ranks (default: PBS_JOBSIZE*PPN)
  --append-eod            Append end-of-document token (default: on)
  --no-append-eod         Disable end-of-document token
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-dir)
      INPUT_DIR="$2"; shift 2 ;;
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --tokenizer-type)
      TOKENIZER_TYPE="$2"; shift 2 ;;
    --tokenizer-model)
      TOKENIZER_MODEL="$2"; shift 2 ;;
    --num-workers)
      NUM_WORKERS="$2"; shift 2 ;;
    --ppn)
      PPN="$2"; shift 2 ;;
    --depth)
      DEPTH="$2"; shift 2 ;;
    --nprocs)
      NPROCS="$2"; shift 2 ;;
    --append-eod)
      APPEND_EOD=1; shift ;;
    --no-append-eod)
      APPEND_EOD=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${TOKENIZER_MODEL}" ]]; then
  echo "ERROR: --tokenizer-model is required." >&2
  exit 1
fi

if [[ ! -d "${INPUT_DIR}" ]]; then
  echo "ERROR: input dir not found: ${INPUT_DIR}" >&2
  exit 1
fi

if ! command -v mpiexec >/dev/null 2>&1; then
  echo "ERROR: mpiexec not found in PATH." >&2
  exit 1
fi

if ! command -v tokenization >/dev/null 2>&1; then
  echo "ERROR: tokenization command not found in PATH (install blendcorpus)." >&2
  exit 1
fi

if [[ -z "${NPROCS}" ]]; then
  if [[ -n "${PBS_JOBSIZE:-}" ]]; then
    NPROCS=$((PBS_JOBSIZE * PPN))
  else
    NPROCS="${PPN}"
  fi
fi

append_flag=""
if [[ "${APPEND_EOD}" -eq 1 ]]; then
  append_flag="--append-eod"
fi

mkdir -p "${OUTPUT_DIR}"

echo "[tokenization] input=${INPUT_DIR} output=${OUTPUT_DIR} tokenizer=${TOKENIZER_TYPE}"
echo "[tokenization] num_workers=${NUM_WORKERS} ppn=${PPN} nprocs=${NPROCS} depth=${DEPTH}"

mpiexec -n "${NPROCS}" --ppn "${PPN}" --cpu-bind depth -d "${DEPTH}" \
  tokenization \
  --input-dir "${INPUT_DIR}" \
  --output-dir "${OUTPUT_DIR}" \
  --num-workers "${NUM_WORKERS}" \
  --tokenizer-type "${TOKENIZER_TYPE}" \
  --tokenizer-model "${TOKENIZER_MODEL}" \
  ${append_flag}

echo "[tokenization] Done"
