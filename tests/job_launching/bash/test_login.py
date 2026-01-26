from clearml import Task

created_task = Task.create(
    project_name = "AmSC",
    task_name = "Workflow login",
    script = "./run_login.sh",
    binary = "/bin/bash",
    force_single_script_file = True
)

Task.enqueue(created_task, queue_name="sirius-login")
