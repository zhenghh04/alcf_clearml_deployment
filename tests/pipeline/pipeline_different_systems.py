from clearml.automation import PipelineDecorator
from clearml import Task
import subprocess
import json
import os

# ------------------------
# Step 0: local
# ------------------------
@PipelineDecorator.component(
    execution_queue="sirius-login",
    docker="python:3.12-slim",
    packages=["clearml==2.1.2"],
)
def generate_config() -> dict:
    
    print("LOCAL: generating config")

    cfg = {
        "nodes": 2,
        "tasks_per_node": 2,
        "output_dir": "/home/hzheng/clearml/tmp/mpi_example"
    }

    os.makedirs(cfg["output_dir"], exist_ok=True)
    with open(os.path.join(cfg["output_dir"], "config.json"), "w") as f:
        json.dump(cfg, f)

    return cfg

# ------------------------
# Step 1: login node
# ------------------------
@PipelineDecorator.component(
    execution_queue="sirius-login",
    docker="python:3.12-slim",
    packages=["clearml==2.1.2"],
)
def stage_metadata(cfg: dict) -> dict:
    print("LOGIN NODE: staging metadata")
    print("Config:", cfg)
    return cfg

# ------------------------
# Step 2: compute nodes (MPI)
# ------------------------
@PipelineDecorator.component(
    execution_queue="sirius",
    docker="python:3.12-slim",
    packages=["clearml==2.1.2"],
)
def run_mpi(cfg: dict) -> dict:
    task = Task.current_task()
    # Tell Slurm how many resources we want
    task.set_user_properties(
        nodes=cfg["nodes"],
        tasks_per_node=cfg["tasks_per_node"]
    )

    print("COMPUTE NODES: launching MPI")

    subprocess.check_call([
        "mpiexec",
        "python",
        "mpi_compute.py"
    ])

    return cfg

# ------------------------
# Step 3: login node
# ------------------------
@PipelineDecorator.component(
    execution_queue="sirius-login",
    docker="python:3.12-slim",
    packages=["clearml==2.1.2"],
)
def collect_results(cfg: dict):
    print("LOGIN NODE: collecting results")
    print("Done.")

# ------------------------
# Pipeline definition
# ------------------------
@PipelineDecorator.pipeline(
    name="pipeline_different_system",
    project="AmSC",
    docker="python:3.12-slim",
)
def pipeline():
    cfg = generate_config()
    cfg = stage_metadata(cfg)
    cfg = run_mpi(cfg)
    collect_results(cfg)

if __name__ == "__main__":
    #PipelineDecorator.run_locally()
    pipeline()
