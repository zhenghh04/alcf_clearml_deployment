# Download CIFAR dataset and create a dataset with ClearML's Dataset class
from clearml import StorageManager, Dataset
import glob
manager = StorageManager()

#dataset_path = manager.get_local_copy(remote_url="https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz")

dataset = Dataset.create(dataset_name="dolma", dataset_project="dataset_examples", dataset_version='1.7', description="Dolma dataset")
files = [f"file://{d}" for d in glob.glob("/eagle/datasets/dolma/data_v1.7/*.gz")]
print(files)
dataset.add_external_files(source_url=files, max_workers=1)
# Prepare and clean data here before it is added to the dataset
#dataset_path="/home/hzheng/clearml/examples/testdata"
#dataset.add_files(path=dataset_path, max_workers=1)

# Dataset is uploaded to the ClearML Server by default
dataset.upload(max_workers=1)

dataset.finalize()
