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
    execution_queue='zion',
    docker="python:3.13-slim",
    packages=["clearml==2.1.3"],
)
def step_local(previous) -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()
    return previous + 1
    

@PipelineDecorator.component(
    execution_queue="sirius-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3"],
)
def step_sirius(previous) -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()
    return previous + 1

@PipelineDecorator.component(
    execution_queue="sophia-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3"],
)
def step_sophia(previous) -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()
    return previous + 1

@PipelineDecorator.component(
    execution_queue="aurora-login",
    docker="python:3.13-slim",
    packages=["clearml==2.1.3"],
)
def step_aurora(previous) -> dict:
    print("Logging to system and writing hello_clearml.txt on home directory")
    f = open(os.path.expanduser("~/hello_clearml.txt"), "w")
    datetime = subprocess.check_output(["date"]).decode("utf-8").strip()
    f.write(f"Hello ClearML on {socket.gethostname()}! Current date and time is: {datetime}\n")
    f.close()
    return previous + 1

# ------------------------
# Pipeline definition
# ------------------------
@PipelineDecorator.pipeline(
    name="pipeline_different_system",
    project="AmSC",
    docker="python:3.10-slim",
)
def pipeline():
    task = Task.current_task()
    if task:
        task.set_packages([])
    a = step_local(0)
    b = step_sirius(a)
    c = step_sophia(b)
    d = step_aurora(b)

if __name__ == "__main__":
    #PipelineDecorator.run_locally()
    pipeline()
