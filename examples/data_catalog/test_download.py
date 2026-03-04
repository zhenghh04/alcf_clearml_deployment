from __future__ import print_function

import os
from clearml import Task, Dataset


def main():
    task = Task.init(
        project_name="AmSC",
        task_name="download-dataset",
        task_type=Task.TaskTypes.data_processing,
    )

    dataset = Dataset.get(
        dataset_name="dolma",
        dataset_project="AuroraGPT",
        dataset_version="1.7",
    )
    local_path = dataset.get_local_copy(target_folder="/tmp/dolma_v1.7", max_workers=1)
    print("Dataset downloaded to:", local_path)

if __name__ == "__main__":
    main()
