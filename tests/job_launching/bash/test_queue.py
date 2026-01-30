from clearml import Task

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--queue", default="crux")
parser.add_argument("--num-nodes", type=int, default=8)
parser.add_argument("--walltime", default="00:10:00")
parser.add_argument("--account", default="datascience")
parser.add_argument("--script", default="./test.py")
parser.add_argument("--pbs-queue", default=None)

args = parser.parse_args()

print("[test_queue] Starting job launch with arguments:")
print(f"  queue={args.queue}")
print(f"  num_nodes={args.num_nodes}")
print(f"  walltime={args.walltime}")
print(f"  account={args.account}")
print(f"  script={args.script}")
print(f"  pbs_queue={args.pbs_queue}")

created_task = Task.create(
    project_name = "AmSC",
    task_name = "PBS Demo bash",
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    script = "tests/job_launching/bash/run.sh",
    working_directory = "./",
    binary = "/bin/bash",
)
created_task.set_user_properties(
    walltime=args.walltime,
    num_nodes=args.num_nodes,
    account=args.account
)
#created_task.set_user_properties(num_nodes={'type':int, "value":2}, walltime={"type":str, "value":"0:10:00"}, account="datascience")

print(f"[test_queue] Created ClearML task id={created_task.id}")
print(f"[test_queue] Enqueuing task to queue '{args.queue}'...")

Task.enqueue(created_task, queue_name=args.queue)

print("[test_queue] Task enqueued successfully.")
