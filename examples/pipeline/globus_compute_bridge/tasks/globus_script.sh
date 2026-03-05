#!/bin/bash
cd $PBS_O_WORKDIR
echo $PWD
echo "Started job $PBS_JOBID on $(hostname) at $(date)"
echo "Running a dummy script on the Globus Compute endpoint..."
echo "Sleeping for 10 seconds to simulate a long-running task..."
echo "Running on nodes: $PBS_NODEFILE"
python -c "import time; time.sleep(10); import socket; print('Hostname:', socket.gethostname())"
export PBS_JOBSIZE=$(cat $PBS_NODEFILE | uniq | wc -l)
export PPN=4
mpiexec -n $((PBS_JOBSIZE*PPN)) --ppn $PPN python -c "from mpi4py import MPI; import socket; comm = MPI.COMM_WORLD; rank = comm.Get_rank(); print(f'I am Rank {rank} of {comm.size()} on {socket.gethostname()}')"
echo "Done sleeping, exiting now."