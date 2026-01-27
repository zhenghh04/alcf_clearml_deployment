from __future__ import print_function

import argparse
import os
import sys
from clearml import Task


def main():
    parser = argparse.ArgumentParser(description="Enqueue MNIST training task")
    parser.add_argument("--clearml-queue", default=os.environ.get("CLEARML_QUEUE"))
    parser.add_argument("--queue", default=os.environ.get("QUEUE", "default"))
    parser.add_argument("--pbs-queue", default=os.environ.get("PBS_QUEUE"))
    parser.add_argument("--walltime", default=os.environ.get("WALLTIME"))
    parser.add_argument("--num-nodes", type=int, default=os.environ.get("NUM_NODES"))
    parser.add_argument("--account", default=os.environ.get("ACCOUNT"))
    parser.add_argument("--no-skip-install", action="store_true", default=False)
    args = parser.parse_args()

    script_path = os.path.join(os.path.dirname(__file__), "pytorch_mnist.py")
    created_task = Task.create(
        project_name="AmSC",
        task_name="PyTorch MNIST train (enqueued)",
        script=script_path,
        force_single_script_file=True,
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

    if not args.no_skip_install:
        created_task.set_environment(
            {
                "CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL": "1",
                "CLEARML_AGENT_SKIP_PIP_VENV_INSTALL": sys.executable,
            }
        )

    clearml_queue = args.clearml_queue or args.queue
    print("Enqueuing task id={} to clearml_queue='{}'".format(created_task.id, clearml_queue))
    Task.enqueue(created_task, queue_name=clearml_queue)


if __name__ == "__main__":
    main()
