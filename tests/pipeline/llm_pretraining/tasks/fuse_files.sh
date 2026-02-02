#!/usr/bin/env bash
set -euo pipefail
# set -x 
# set conda environment

export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
source /eagle/AuroraGPT/hzheng/pyenvs/blendcorpus/bin/activate
INPUT_DIR="${FUSE_INPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data}"
OUTPUT_DIR="${FUSE_OUTPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data-fused}"
PPN="${FUSE_PPN:-4}"
THREADS_PER_RANK="${FUSE_THREADS_PER_RANK:-4}"
DEPTH="${FUSE_DEPTH:-}"
NPROCS="${FUSE_NPROCS:-}"

usage() {
  cat <<'USAGE'
Usage: fuse_files.sh [options]

Options:
  --input-dir PATH         Input directory (default: /eagle/AuroraGPT/datasets/data)
  --output-dir PATH        Output directory (default: /eagle/AuroraGPT/datasets/data-fused)
  --ppn N                  MPI ranks per node (default: 4)
  --threads-per-rank N     Threads per rank (default: 4)
  --depth N                CPU bind depth (default: threads-per-rank)
  --nprocs N               Override total MPI ranks (default: PBS_JOBSIZE*PPN)
  -h, --help               Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-dir)
      INPUT_DIR="$2"; shift 2 ;;
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --ppn)
      PPN="$2"; shift 2 ;;
    --threads-per-rank)
      THREADS_PER_RANK="$2"; shift 2 ;;
    --depth)
      DEPTH="$2"; shift 2 ;;
    --nprocs)
      NPROCS="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${DEPTH}" ]]; then
  DEPTH="${THREADS_PER_RANK}"
fi

if [[ ! -d "${INPUT_DIR}" ]]; then
  echo "ERROR: input dir not found: ${INPUT_DIR}" >&2
  exit 1
fi

if ! command -v mpiexec >/dev/null 2>&1; then
  echo "ERROR: mpiexec not found in PATH." >&2
  exit 1
fi

if ! command -v launcher.sh >/dev/null 2>&1; then
  echo "ERROR: launcher.sh not found in PATH (install blendcorpus)." >&2
  exit 1
fi

if ! command -v fuse_files_parallel.sh >/dev/null 2>&1; then
  echo "ERROR: fuse_files_parallel.sh not found in PATH (install blendcorpus)." >&2
  exit 1
fi

if [[ -z "${NPROCS}" ]]; then
  if [[ -n "${PBS_JOBSIZE:-}" ]]; then
    NPROCS=$((PBS_JOBSIZE * PPN))
  else
    NPROCS="${PPN}"
  fi
fi

export PPN
export THREADS_PER_RANK
export ROOT="${INPUT_DIR}"
export OUT="${OUTPUT_DIR}"

mkdir -p "${OUTPUT_DIR}"

echo "[fuse] input=${INPUT_DIR} output=${OUTPUT_DIR}"
echo "[fuse] ppn=${PPN} threads_per_rank=${THREADS_PER_RANK} nprocs=${NPROCS} depth=${DEPTH}"

mpiexec -n "${NPROCS}" --ppn "${PPN}" --cpu-bind depth -d "${DEPTH}" \
  launcher.sh fuse_files_parallel.sh

echo "[fuse] Done"
