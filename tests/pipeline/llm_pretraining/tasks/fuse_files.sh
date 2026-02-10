#!/usr/bin/env bash
# set -x 
# set conda environment
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
source /eagle/AuroraGPT/hzheng/pyenvs/blendcorpus/bin/activate

INPUT_DIR="${FUSE_INPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data}"
OUTPUT_DIR="${FUSE_OUTPUT_DIR:-/eagle/AuroraGPT/hzheng/datasets/data-fused}"


export PBS_JOBSIZE=$(cat $PBS_NODEFILE | uniq | wc -l)

export PPN=4
export THREADS_PER_RANK=1
export DEPTH=16

usage() {
  cat <<'USAGE'
Usage: fuse_files.sh [options]

Options:
  --input-dir PATH         Input directory (default: /eagle/AuroraGPT/datasets/data)
  --output-dir PATH        Output directory (default: /eagle/AuroraGPT/datasets/data-fused)
  --ppn N                  MPI ranks per node (default: 4)
  --depth N                CPU bind depth (default: threads-per-rank)
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
    --depth)
      DEPTH="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

export NPROCS=$((PBS_JOBSIZE * PPN))
export THREADS_PER_RANK=1
export ROOT="${INPUT_DIR}"
export OUT="${OUTPUT_DIR}"

mkdir -p "${OUTPUT_DIR}"

echo "[fuse] input=${INPUT_DIR} output=${OUTPUT_DIR}"
echo "[fuse] ppn=${PPN} nprocs=${NPROCS} depth=${DEPTH}"

mpiexec -n "${NPROCS}" --ppn "${PPN}" --cpu-bind depth -d "${DEPTH}" \
  launcher.sh fuse_files_parallel.sh

echo "[fuse] Done"
