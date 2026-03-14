# Download CIFAR dataset and create a dataset with ClearML's Dataset class
from clearml import Task, Dataset
import glob

task = Task.init(project_name="AuroraGPT", task_name="register_dolma_dataset")

# Because the dataset files are already on the same server as the ClearML agent, 
# we can skip the data movement step and directly register the dataset with ClearML. 
# If the files were on a different server, we could use Globus to transfer them to the ClearML agent's server first, and then register the dataset with ClearML.
task.execute_remotely(queue_name="crux-services", exit_process=True)

dataset = Dataset.create(
    dataset_name="dolma",
    dataset_project="AuroraGPT",
    dataset_version="1.7",
    description="Dolma dataset",
)

files = [f"file://{p}" for p in glob.glob("/eagle/datasets/dolma/data_v1.7/*.gz")]
dataset.add_external_files(source_url=files, max_workers=1)
dataset.upload(max_workers=1)
dataset.finalize()