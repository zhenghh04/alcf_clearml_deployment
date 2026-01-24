from clearml import Task
created_task = Task.create(
    project_name = "AmSC",
    task_name = "PBS Demo",
    script = "./test.py"
)

created_task.set_user_properties(num_nodes=1, walltime=60)
Task.enqueue(created_task, queue_name="default")
