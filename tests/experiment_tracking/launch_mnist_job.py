import argparse
import os
import sys
from clearml import Task


def main():
    parser = argparse.ArgumentParser(description="Enqueue MNIST training task")
    parser.add_argument("--clearml-queue", default="sophia")
    parser.add_argument("--pbs-queue", default="workq")
    parser.add_argument("--walltime", default=os.environ.get("WALLTIME"))
    parser.add_argument("--num-nodes", type=int, default=os.environ.get("NUM_NODES"))
    parser.add_argument("--account", default=os.environ.get("ACCOUNT"))
    parser.add_argument("--no-skip-install", action="store_true", default=False)
    args = parser.parse_args()

    created_task = Task.create(
        project_name="AmSC",
        task_name="PyTorch MNIST train (enqueued)",
        repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
        branch="main",        
        script="tests/experiment_tracking/pytorch_mnist.py",
    )
    user_props = {}
    if args.pbs_queue:
        user_props["queue"] = args.pbs_queue
    if args.walltime:
        user_props["walltime"] = args.walltime
    if args.num_nodes is not None:
        user_props["num_nodes"] = args.num_nodes
    if args.account:
        user_props["account"] = args.account
    if user_props:
        created_task.set_user_properties(**user_props)

    print("Enqueuing task id={} to clearml_queue='{}'".format(created_task.id, args.clearml_queue))
    Task.enqueue(created_task, queue_name=args.clearml_queue)


if __name__ == "__main__":
    main()
