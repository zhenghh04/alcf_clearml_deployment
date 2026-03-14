#!/bin/bash
echo "`date` on $HOSTNAME"
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
mkdir -p $HOME/clearml/tmp/
cp Miniconda3-latest-Linux-x86_64.sh $HOME/clearml/tmp/
echo "`date` done"
