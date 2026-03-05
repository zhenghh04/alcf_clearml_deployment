import argparse
import os
import time

from clearml import Task


def init_subtask(task_index: int) -> Task:
    kwargs = dict(
        project_name="AmSC",
        task_name=f"Ensamble subtask {task_index}",
        task_type=Task.TaskTypes.training,
    )
    try:
        task = Task.init(**kwargs, reuse_last_task_id=False)
    except TypeError:
        task = Task.init(**kwargs)

    parent_task_id = os.environ.get("CLEARML_PARENT_TASK_ID")
    if parent_task_id and hasattr(task, "set_parent"):
        try:
            task.set_parent(parent_task_id)
        except Exception:
            pass

    return task


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-index", type=int, required=True)
    parser.add_argument("--nodes", required=True)
    args = parser.parse_args()

    task = init_subtask(args.task_index)
    logger = task.get_logger()
    print(f"[subtask {args.task_index}] clearml_task_id={task.id}")
    if hasattr(task, "get_output_log_web_page"):
        try:
            print(
                f"[subtask {args.task_index}] clearml_results={task.get_output_log_web_page()}"
            )
        except Exception:
            pass
    logger.report_text(f"Running subtask {args.task_index} on nodes: {args.nodes}")
    print(f"[subtask {args.task_index}] nodes={args.nodes}")

    time.sleep(3)
    print(f"[subtask {args.task_index}] Done")


if __name__ == "__main__":
    main()
