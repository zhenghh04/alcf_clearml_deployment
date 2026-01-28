#!/bin/bash
echo "`date`  Data moving with globus from EAGLE to FLARE..."

python ./tasks/transfer_globus.py \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path /datascience/hzheng/clearml/data/cifar10/cifar-10-python.tar.gz \
  --dst-path /datascience/hzheng/clearml/data/cifar10/cifar-10-python.tar.gz \
  --recursive \
  --poll-interval 5

echo "`date`  Data preparation done!"
