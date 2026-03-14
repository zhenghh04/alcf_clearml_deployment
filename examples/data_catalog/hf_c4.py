from clearml import Dataset, Task
from huggingface_hub import HfApi
task = Task.init(project_name="AuroraGPT", task_name="register_hf_dataset")
task.execute_remotely(queue_name="crux-services", exit_process=True)
repo_id = "allenai/c4"
revision = "main"  # replace with commit SHA once resolved

api = HfApi()
info = api.dataset_info(repo_id, revision=revision)
pinned_revision = info.sha  # immutable commit
print(f"Pinned HF dataset {repo_id} to revision {pinned_revision}")
files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", revision=pinned_revision)
print(f"Found {len(files)} files in the HF dataset repo")
# Keep only data files you actually need
wanted_ext = (".jsonl", ".json.gz", ".zst", ".parquet", ".txt", ".tar", ".tar.gz")
urls = [
    f"https://huggingface.co/datasets/{repo_id}/resolve/{pinned_revision}/{path}"
    for path in files
    if path.endswith(wanted_ext)
]

print(f"Adding {len(urls)} files to ClearML dataset")

ds = Dataset.create(
    dataset_project="AmSC",
    dataset_name="allenai-c4",
    dataset_version="1.0.0",
    description=f"External links pinned to HF commit {pinned_revision}",
)
ds.add_external_files(source_url=urls, max_workers=1)
ds.upload(max_workers=1) 
ds.finalize()
