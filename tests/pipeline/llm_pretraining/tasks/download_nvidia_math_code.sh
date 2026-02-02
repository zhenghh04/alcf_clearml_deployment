#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DOWNLOAD_DATA_ROOT:-/eagle/AuroraGPT/hzheng/datasets}"
MATH_REPO="${DOWNLOAD_MATH_REPO:-nvidia/Nemotron-Math-v2}"
CODE_REPO="${DOWNLOAD_CODE_REPO:-nvidia/Nemotron-Pretraining-Code-v2}"
MODE="${DOWNLOAD_MODE:-both}"

usage() {
  cat <<'USAGE'
Usage: download_nvidia_math_code.sh [options]

Options:
  --data-root PATH   Output root (default: /eagle/AuroraGPT/hzheng/datasets)
  --math-repo NAME   Math dataset repo (default: nvidia/Nemotron-Math-v2)
  --code-repo NAME   Code dataset repo (default: nvidia/Nemotron-Pretraining-Code-v2)
  --mode MODE        math|code|both (default: both)
  -h, --help         Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-root)
      DATA_ROOT="$2"; shift 2 ;;
    --math-repo)
      MATH_REPO="$2"; shift 2 ;;
    --code-repo)
      CODE_REPO="$2"; shift 2 ;;
    --mode)
      MODE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "${DATA_ROOT}"

# If the datasets require auth, export HF_TOKEN before running:
# export HF_TOKEN=your_hf_token

download_repo() {
  local repo="$1"
  echo "[download] Dataset -> ${DATA_ROOT}/${repo}"
  python - "$repo" "$DATA_ROOT" <<'PY'
import os
import sys
from huggingface_hub import snapshot_download

repo = sys.argv[1]
root = sys.argv[2]
token = os.environ.get("HF_TOKEN")

snapshot_download(
    repo_id=repo,
    repo_type="dataset",
    local_dir=os.path.join(root, repo),
    local_dir_use_symlinks=False,
    token=token,
)
PY
}

case "${MODE}" in
  math)
    download_repo "${MATH_REPO}"
    ;;
  code)
    download_repo "${CODE_REPO}"
    ;;
  both)
    download_repo "${MATH_REPO}" &
    math_pid=$!
    download_repo "${CODE_REPO}" &
    code_pid=$!
    wait "${math_pid}" "${code_pid}"
    ;;
  *)
    echo "ERROR: unknown DOWNLOAD_MODE: ${MODE} (expected: math|code|both)" >&2
    exit 1
    ;;
esac

echo "[download] Done"
