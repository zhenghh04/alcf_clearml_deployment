# Download CIFAR dataset and create a dataset with ClearML's Dataset class
from clearml import StorageManager, Dataset

manager = StorageManager()

#dataset_path = manager.get_local_copy(remote_url="https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz")

dataset = Dataset.create(dataset_name="test_dataset_ext_link", dataset_project="dataset_examples")
dataset.add_external_files(source_url="file:///home/hzheng/clearml/examples/testdata/a.dat")
# Dataset is uploaded to the ClearML Server by default
dataset.upload(max_workers=1)

dataset.finalize()
