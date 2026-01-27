#!/bin/bash
set -euo pipefail

echo "  Evaluating model..."
python evaluate.py \
  --data-dir "${CIFAR10_DIR:-${CIFAR10_DOWNLOAD_DIR:-/tmp/cifar10}}" \
  --batch-size 128 \
  --num-workers 4 \
  --checkpoint "${RESNET50_CKPT:-/tmp/resnet50_cifar10.pt}"
