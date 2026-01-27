#!/bin/bash
set -euo pipefail
echo "`date`  Training model..."
python resnet50.py \
  --data-dir "${CIFAR10_DIR:-/tmp/cifar10}" \
  --epochs 1 \
  --batch-size 128 \
  --lr 0.01 \
  --num-workers 4 \
  --download \
  --checkpoint "${RESNET50_CKPT:-/tmp/resnet50_cifar10.pt}"
echo " `date` Done! Model saved to ${RESNET50_CKPT:-/tmp/resnet50_cifar10.pt}"
#-- END OF FILE --