from clearml import Task

created_task = Task.create(
    project_name = "AmSC",
    task_name = "PBS Demo bash",
    script = "./run.sh",
    binary = "/bin/bash"
)
created_task.set_user_properties(
    walltime="00:10:00",
    num_nodes=8,
    account="datascience"
)
#created_task.set_user_properties(num_nodes={'type':int, "value":2}, walltime={"type":str, "value":"0:10:00"}, account="datascience")

Task.enqueue(created_task, queue_name="crux")
