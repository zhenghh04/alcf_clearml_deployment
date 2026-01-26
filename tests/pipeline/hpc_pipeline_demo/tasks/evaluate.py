from clearml import Task


task = Task.init(
    project_name="amsc/pipeline-demo",
    task_name="evaluate-model",
    task_type=Task.TaskTypes.testing,
)

print("Evaluating model...")
