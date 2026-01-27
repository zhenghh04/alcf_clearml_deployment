from __future__ import print_function

import os
from clearml import Task


def main():
    script_path = os.path.join(os.path.dirname(__file__), "pytorch_mnist.py")
    created_task = Task.create(
        project_name="AmSC",
        task_name="PyTorch MNIST train (enqueued)",
        script=script_path,
        force_single_script_file=True,
    )
    queue_name = os.environ.get("QUEUE", "default")
    print("Enqueuing task id={} to queue='{}'".format(created_task.id, queue_name))
    Task.enqueue(created_task, queue_name=queue_name)


if __name__ == "__main__":
    main()
