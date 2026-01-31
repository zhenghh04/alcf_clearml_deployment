from clearml import Task

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--queue", default="crux")
parser.add_argument("--num-nodes", type=int, default=6)
parser.add_argument("--walltime", default="00:30:00")
parser.add_argument("--account", default="datascience")
args = parser.parse_args()

created_task = Task.create(
    project_name="AmSC",
    task_name="Pattern B: single allocation runner",
    task_type=Task.TaskTypes.training,
    repo="git@github.com:zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    script="tests/job_launching/pattern_b/run_local_tasks.py",
    working_directory="./",
    binary="python",
)
created_task.set_user_properties(
    walltime=args.walltime,
    num_nodes=args.num_nodes,
    account=args.account,
)

Task.enqueue(created_task, queue_name=args.queue)
print(f"Enqueued Ensamble runner to queue '{args.queue}' as task {created_task.id}")