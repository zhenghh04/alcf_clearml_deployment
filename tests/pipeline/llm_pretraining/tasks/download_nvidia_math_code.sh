#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/eagle/AuroraGPT/datasets"
MATH_REPO="nvidia/Nemotron-CC-Math-v1"
CODE_REPO="nvidia/Nemotron-CC-Code-v1"

mkdir -p "${DATA_ROOT}"

# If the datasets require auth, export HF_TOKEN before running:
# export HF_TOKEN=your_hf_token

echo "[download] Math dataset -> ${DATA_ROOT}/${MATH_REPO}"
huggingface-cli download \
  --repo-type dataset \
  --local-dir "${DATA_ROOT}/${MATH_REPO}" \
  --local-dir-use-symlinks False \
  "${MATH_REPO}"

echo "[download] Code dataset -> ${DATA_ROOT}/${CODE_REPO}"
huggingface-cli download \
  --repo-type dataset \
  --local-dir "${DATA_ROOT}/${CODE_REPO}" \
  --local-dir-use-symlinks False \
  "${CODE_REPO}"

echo "[download] Done"
