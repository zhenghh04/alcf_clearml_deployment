from __future__ import print_function

import os
import tarfile
import urllib.request
from clearml import Task, Dataset


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

    dataset_name = os.environ.get("CIFAR10_DATASET_NAME", "cifar10")
    dataset_project = os.environ.get("CIFAR10_DATASET_PROJECT", "amsc/pipeline-demo")
    dataset_version = os.environ.get("CIFAR10_DATASET_VERSION")

    print("Uploading dataset to ClearML fileserver...")
    dataset = Dataset.create(
        dataset_name=dataset_name,
        dataset_project=dataset_project,
        dataset_version=dataset_version,
    )
    dataset.add_files(path=data_dir, recursive=True)
    dataset.upload()
    dataset.finalize()
    print("Dataset uploaded:", dataset.id)


if __name__ == "__main__":
    main()
