#!/bin/bash
echo "Job started at `date`"
echo $PWD
ls 
which python
PBS_JOBSIZE=$(cat $PBS_NODEFILE | uniq | wc -l)
PPN=32
mpiexec -np $((PBS_JOBSIZE*PPN)) --ppn $PPN --hostfile=$PBS_NODEFILE python -c "from mpi4py import MPI; import socket; comm=MPI.COMM_WORLD; print(f'I am {comm.rank} of {comm.size} on {socket.gethostname()}')"
echo $PBS_NODEFILE
echo "Job finished at `date`"

