import argparse
import json
import operator
import time
from pathlib import Path
from typing import Any, Dict, Optional

from clearml import Task
from globus_compute_sdk import Executor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="amsc/pipeline-globus-bridge")
    parser.add_argument("--bridge-tag", default="globus-bridge")
    parser.add_argument("--endpoint-id", required=True)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--task-timeout-sec", type=int, default=1800)
    return parser.parse_args()


def read_param(params: Dict[str, Any], name: str, default: Optional[str] = None) -> Optional[str]:
    candidate_suffixes = [
        f"/{name}",
        f"/{name.replace('_', '-')}",
        f"/{name.replace('-', '_')}",
    ]
    for key, value in params.items():
        for suffix in candidate_suffixes:
            if key.endswith(suffix):
                return str(value)
    return default


def fetch_candidates(project: str, bridge_tag: str) -> list:
    return Task.get_tasks(
        project_name=project,
        tags=[bridge_tag],
        allow_archived=False,
        task_filter={"status": [Task.TaskStatusEnum.queued.value]},
    )


def execute_via_globus(task: Task, endpoint_id: str, task_timeout_sec: int) -> dict:
    params = task.get_parameters_as_dict(cast=True)
    input_value = int(read_param(params, "input_value", default="7"))

    start = time.time()
    logger = task.get_logger()
    logger.report_text(
        f"Bridge worker submitting task {task.id} with input_value={input_value}"
    )

    with Executor(endpoint_id=endpoint_id) as executor:
        # Use stdlib callable to avoid Python minor-version bytecode mismatch issues.
        future = executor.submit(operator.mul, input_value, input_value)
        while not future.done():
            elapsed = time.time() - start
            logger.report_scalar(
                "bridge_worker", "wait_time_sec", value=elapsed, iteration=int(elapsed)
            )
            if elapsed > task_timeout_sec:
                raise TimeoutError(
                    f"Timed out waiting for Globus task after {task_timeout_sec}s"
                )
            time.sleep(5)
        output_value = future.result()

    result = {
        "input": input_value,
        "output": output_value,
        "message": "Executed on Globus Compute endpoint",
    }

    logger.report_scalar("bridge_worker", "result", value=result["output"], iteration=0)
    return result


def main() -> int:
    args = parse_args()

    service_task = Task.init(
        project_name=args.project,
        task_name="globus-bridge-worker",
        task_type=Task.TaskTypes.service,
    )
    service_task.connect(vars(args), name="worker")
    service_logger = service_task.get_logger()

    service_logger.report_text(
        f"Bridge worker started: project={args.project}, tag={args.bridge_tag}"
    )

    while True:
        candidates = fetch_candidates(args.project, args.bridge_tag)
        if not candidates:
            time.sleep(args.poll_interval)
            continue

        for queued_task in candidates:
            task = Task.get_task(task_id=queued_task.id)
            if task.status != Task.TaskStatusEnum.queued:
                continue

            try:
                Task.dequeue(task=task)
                task.mark_started(force=True)
            except Exception as exc:
                service_logger.report_text(
                    f"Skip task {task.id}: could not claim queued task ({exc})"
                )
                continue

            try:
                result = execute_via_globus(
                    task=task,
                    endpoint_id=args.endpoint_id,
                    task_timeout_sec=args.task_timeout_sec,
                )
                artifact_path = Path(f"bridge_result_{task.id}.json")
                artifact_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                task.upload_artifact("globus_result", str(artifact_path))
                task.mark_completed(
                    status_message=f"Globus task succeeded with output={result['output']}"
                )
                service_logger.report_text(f"Task {task.id} completed via Globus")
            except Exception as exc:
                task.mark_failed(status_reason="Globus bridge execution failed", status_message=str(exc))
                service_logger.report_text(f"Task {task.id} failed: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
