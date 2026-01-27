from clearml.automation import PipelineDecorator
from clearml import Task
import os
os.environ.setdefault("CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL", "1")
os.environ.setdefault("CLEARML_AGENT_SKIP_PIP_VENV_INSTALL", "/usr/bin/python3")
import subprocess
import json
import socket

# ------------------------
# Step 0: local
# ------------------------

@PipelineDecorator.component(
    execution_queue=None,
    docker="python:3.13-slim",
    packages=["clearml==2.1.3", "torchvision==0.15.2", "torch==2.10"],
)
def step_local() -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()

@PipelineDecorator.component(
    execution_queue="sirius-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3", "torchvision==0.15.2", "torch==2.10"],
)
def step_sirius() -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()

@PipelineDecorator.component(
    execution_queue="sophia-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3", "torchvision==0.15.2", "torch==2.10"],
)
def step_sophia() -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()

@PipelineDecorator.component(
    execution_queue="aurora-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3", "torchvision==0.15.2", "torch==2.10"],
)
def step_aurora() -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()

# ------------------------
# Pipeline definition
# ------------------------
@PipelineDecorator.pipeline(
    name="pipeline_different_system",
    project="AmSC",
    docker="python:3.13-slim",
)
def pipeline():
    task = Task.current_task()
    if task:
        task.set_packages(["clearml==2.1.3", "torchvision==0.15.2", "torch==2.10"])
    step_local()
    step_sirius()
    step_sophia()
    step_aurora()

if __name__ == "__main__":
    #PipelineDecorator.run_locally()
    pipeline()
