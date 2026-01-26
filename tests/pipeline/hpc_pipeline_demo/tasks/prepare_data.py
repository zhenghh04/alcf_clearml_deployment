from clearml import Task


task = Task.init(
    project_name="amsc/pipeline-demo",
    task_name="prepare-data",
    task_type=Task.TaskTypes.data_processing,
)

print("Preparing data...")
