#!/bin/bash
echo "`date`  Preparing data..."
export DST=/eagle/datascience/hzheng/clearml/data/cifar10/
mkdir -p $DST
wget -c -P $DST https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz