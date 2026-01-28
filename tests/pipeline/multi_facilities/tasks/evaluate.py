from __future__ import print_function

import os
import subprocess
from clearml import Task


def main():
    task = Task.init(
        project_name="amsc/pipeline-demo",
        task_name="evaluate-model",
        task_type=Task.TaskTypes.testing,
    )
    print("Evaluate model task registered.")
    try:
        if task.running_locally():
            return
    except Exception:
        pass

    script_path = os.path.join(os.path.dirname(__file__), "evaluate.sh")
    subprocess.check_call(["/bin/bash", script_path])


if __name__ == "__main__":
    main()
