#!/bin/bash
set -euo pipefail

python train.py \
  --data-dir "${CIFAR10_DIR:-/tmp/cifar10}" \
  --epochs 1 \
  --batch-size 128 \
  --lr 0.01 \
  --num-workers 4 \
  --checkpoint "${RESNET50_CKPT:-/tmp/resnet50_cifar10.pt}"
