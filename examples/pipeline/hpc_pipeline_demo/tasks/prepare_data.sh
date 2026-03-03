#!/bin/bash
mkdir -p $HOME/clearml/alcf_clearml_evaluation/tests/hpc_pipeline_demo/
export DST=$HOME/clearml/alcf_clearml_evaluation/tests/hpc_pipeline_demo/
wget -c -P $DST https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
