from __future__ import print_function

import os
import tarfile
import urllib.request
from clearml import Task


def _download(url, dest_path):
    if os.path.exists(dest_path):
        return dest_path
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    urllib.request.urlretrieve(url, dest_path)
    return dest_path


def _extract(tar_path, out_dir):
    if os.path.exists(out_dir) and os.listdir(out_dir):
        return
    os.makedirs(out_dir, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=out_dir)


def main():
    task = Task.init(
        project_name="amsc/pipeline-demo",
        task_name="prepare-data",
        task_type=Task.TaskTypes.data_processing,
    )

    try:
        if task.running_locally():
            print("Task registered (prepare-data). Run via pipeline/agent to execute.")
            return
    except Exception:
        pass

    data_dir = os.environ.get("CIFAR10_DIR", "/tmp/cifar10")
    url = "https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"
    tar_path = os.path.join(data_dir, "cifar-10-python.tar.gz")

    print("Preparing data...")
    _download(url, tar_path)
    _extract(tar_path, data_dir)
    print("CIFAR-10 available at:", data_dir)


if __name__ == "__main__":
    main()
