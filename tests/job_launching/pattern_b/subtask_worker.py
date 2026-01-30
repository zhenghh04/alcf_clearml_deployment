import argparse
import time

from clearml import Task


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-index", type=int, required=True)
    parser.add_argument("--nodes", required=True)
    args = parser.parse_args()

    task = Task.init(
        project_name="AmSC",
        task_name=f"Pattern B subtask {args.task_index}",
        task_type=Task.TaskTypes.training,
    )
    logger = task.get_logger()
    logger.report_text(f"Running subtask {args.task_index} on nodes: {args.nodes}")
    print(f"[subtask {args.task_index}] nodes={args.nodes}")

    time.sleep(3)
    print(f"[subtask {args.task_index}] Done")


if __name__ == "__main__":
    main()