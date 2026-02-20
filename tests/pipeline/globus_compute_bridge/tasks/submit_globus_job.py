import argparse
import json
import operator
import os
import time
from pathlib import Path
from typing import Any, Dict

from clearml import Task
from globus_compute_sdk import Executor

DEFAULT_ENDPOINT_ID = "fad4d968-8c9a-45ce-9fb4-60a9ab90be60"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint-id",
        default=os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", DEFAULT_ENDPOINT_ID),
    )
    parser.add_argument("--input-value", type=int, default=7)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--artifact-path", default="globus_result.json")
    return parser.parse_args()


def flatten_params(params: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in params.items():
        full_key = f"{prefix}/{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(flatten_params(value, full_key))
        else:
            flattened[full_key] = value
    return flattened


def read_param(params: Dict[str, Any], name: str) -> str:
    flat = flatten_params(params)
    candidate_suffixes = [
        f"/{name}",
        f"/{name.replace('_', '-')}",
        f"/{name.replace('-', '_')}",
        f"/--{name.replace('_', '-')}",
    ]
    for key, value in flat.items():
        for suffix in candidate_suffixes:
            if key.endswith(suffix) and value not in (None, ""):
                return str(value)
    return ""


def main() -> int:
    args = parse_args()

    task = Task.init(
        project_name="amsc/pipeline-globus-bridge",
        task_name="submit-globus-compute-job",
        task_type=Task.TaskTypes.data_processing,
    )
    task.connect(vars(args), name="bridge")
    logger = task.get_logger()

    task_params = task.get_parameters_as_dict(cast=True)
    endpoint_id = args.endpoint_id or read_param(task_params, "endpoint_id")
    if not endpoint_id:
        logger.report_text(f"Parameter keys visible to task: {sorted(flatten_params(task_params).keys())}")
        raise ValueError(
            "endpoint-id is required. Set --endpoint-id or GLOBUS_COMPUTE_ENDPOINT_ID."
        )

    start = time.time()
    logger.report_text(
        f"Submitting payload={args.input_value} to Globus endpoint {endpoint_id}"
    )

    my_config = {"account": "datascience"}

    with Executor(endpoint_id=endpoint_id, user_endpoint_config=my_config) as executor:
        # Use stdlib callable to avoid Python minor-version bytecode mismatch issues.
        future = executor.submit(operator.mul, args.input_value, args.input_value)
        while not future.done():
            elapsed = time.time() - start
            logger.report_scalar(
                "globus_bridge", "wait_time_sec", value=elapsed, iteration=int(elapsed)
            )
            if elapsed > args.timeout_sec:
                raise TimeoutError(
                    f"Timed out waiting for Globus task after {args.timeout_sec}s"
                )
            time.sleep(args.poll_interval)

        output_value = future.result()

    result = {
        "input": args.input_value,
        "output": output_value,
        "message": "Executed on Globus Compute endpoint",
    }

    elapsed = time.time() - start
    logger.report_scalar("globus_bridge", "total_time_sec", value=elapsed, iteration=0)
    logger.report_scalar("globus_bridge", "output", value=result["output"], iteration=0)

    artifact_path = Path(args.artifact_path)
    artifact_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    task.upload_artifact(name="globus_result", artifact_object=str(artifact_path))
    logger.report_text(f"Completed Globus Compute execution: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
