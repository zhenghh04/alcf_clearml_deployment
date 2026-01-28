from clearml import Task

created_task = Task.create(
    project_name = "AmSC",
    task_name = "Workflow login",
    repo="https://github.com/zhenghh04/alcf_clearml_evaluation.git",
    branch="main",
    script = "tests/job_launching/bash/run_login.sh",
    working_directory = "./",
    binary = "/bin/bash",
)

Task.enqueue(created_task, queue_name="sirius-login")
