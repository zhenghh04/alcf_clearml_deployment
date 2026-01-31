#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DOWNLOAD_DATA_ROOT:-/eagle/AuroraGPT/hzheng/}"
MATH_REPO="${DOWNLOAD_MATH_REPO:-nvidia/Nemotron-Math-v2}"
CODE_REPO="${DOWNLOAD_CODE_REPO:-nvidia/Nemotron-Pretraining-Code-v2}"
MODE="${DOWNLOAD_MODE:-both}"

mkdir -p "${DATA_ROOT}"

# If the datasets require auth, export HF_TOKEN before running:
# export HF_TOKEN=your_hf_token

download_repo() {
  local repo="$1"
  echo "[download] Dataset -> ${DATA_ROOT}/${repo}"
  huggingface-cli download \
    --repo-type dataset \
    --local-dir "${DATA_ROOT}/${repo}" \
    --local-dir-use-symlinks False \
    "${repo}"
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
