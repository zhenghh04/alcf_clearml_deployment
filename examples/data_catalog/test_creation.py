from __future__ import print_function

from clearml import Dataset


DATASET_NAME = "test_dataset"
DATASET_PROJECT = "dataset_examples"
DATASET_PATH = "./testdata"
DOWNLOAD_TARGET = "/tmp/test_dataset_download"


dataset = Dataset.create(dataset_name=DATASET_NAME, dataset_project=DATASET_PROJECT)

# Prepare and clean data here before it is added to the dataset.
dataset.add_files(path=DATASET_PATH, max_workers=1)

# Dataset is uploaded to the ClearML Server by default.
dataset.upload(max_workers=1)
dataset.finalize()

downloaded_dataset = Dataset.get(dataset_id=dataset.id)
local_path = downloaded_dataset.get_local_copy(
    target_folder=DOWNLOAD_TARGET,
    max_workers=1,
)

print("Created dataset id:", dataset.id)
print("Dataset downloaded to:", local_path)
