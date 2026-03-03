from clearml import Task
import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--queue", default="crux-login")
args = parser.parse_args()

created_task = Task.create(
    project_name = "AmSC",
    task_name = "Workflow login",
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    script = "examples/job_launching/bash/run_login.sh",
    working_directory = "./",
    binary = "/bin/bash",
)

Task.enqueue(created_task, queue_name=args.queue)
