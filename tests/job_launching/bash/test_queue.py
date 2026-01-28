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

created_task = Task.create(
    project_name = "AmSC",
    task_name = "PBS Demo bash",
    script = "tests/jobs_launching/bash/run.sh",
    binary = "/bin/bash",
    repo = "https://github.com/zhenghh04/alcf_clearml_evaluation.git",
)
created_task.set_user_properties(
    walltime=args.walltime,
    num_nodes=args.num_nodes,
    account=args.account
)
#created_task.set_user_properties(num_nodes={'type':int, "value":2}, walltime={"type":str, "value":"0:10:00"}, account="datascience")

Task.enqueue(created_task, queue_name=args.queue)
