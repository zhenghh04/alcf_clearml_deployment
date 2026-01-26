from clearml import Task


task = Task.init(
    project_name="amsc/pipeline-demo",
    task_name="train-model",
    task_type=Task.TaskTypes.training,
)
task.set_base_docker(docker_image=None)
print("Training model...")
