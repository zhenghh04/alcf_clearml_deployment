#!/usr/bin/env python
import time
import os
print("start running")
nodefile = os.environ['PBS_NODEFILE']
os.system(f"mpiexec -np 128 --hostfile={nodefile} /home/hzheng/clearml/pi_mpi4py.py --samples 100000000")
