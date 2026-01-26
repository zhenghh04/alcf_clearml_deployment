from clearml import Task


task = Task.init(
    project_name="amsc/pipeline-demo",
    task_name="evaluate-model",
    task_type=Task.TaskTypes.testing,
)
task.set_base_docker(docker_image=None)
print("Evaluating model...")
