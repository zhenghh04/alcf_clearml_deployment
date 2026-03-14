from __future__ import print_function

import os
from clearml import Task, Dataset


def main():
    task = Task.init(
        project_name="amsc/pipeline-demo",
        task_name="move-dataset",
        task_type=Task.TaskTypes.data_processing,
    )


    dataset_project = os.environ.get("CIFAR10_DATASET_PROJECT", "amsc/pipeline-demo")
    dataset_name = os.environ.get("CIFAR10_DATASET_NAME", "cifar10")
    dataset_version = os.environ.get("CIFAR10_DATASET_VERSION")
    target_dir = os.environ.get("CIFAR10_DOWNLOAD_DIR", "/tmp/cifar10_download")

    dataset = Dataset.get(
        dataset_project=dataset_project,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
    )
    local_path = dataset.get_local_copy(target_folder=target_dir)
    print("Dataset downloaded to:", local_path)


if __name__ == "__main__":
    main()
