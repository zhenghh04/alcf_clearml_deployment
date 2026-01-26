from clearml import Task


task = Task.init(
    project_name="amsc/pipeline-demo",
    task_name="train-model",
    task_type=Task.TaskTypes.training,
)

print("Training model...")
