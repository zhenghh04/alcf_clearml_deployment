import argparse
import json
import operator
import time
from pathlib import Path

from clearml import Task
from globus_compute_sdk import Executor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-id", required=True)
    parser.add_argument("--input-value", type=int, default=7)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--artifact-path", default="globus_result.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    task = Task.init(
        project_name="amsc/pipeline-globus-bridge",
        task_name="submit-globus-compute-job",
        task_type=Task.TaskTypes.data_processing,
    )
    task.connect(vars(args), name="bridge")
    logger = task.get_logger()

    start = time.time()
    logger.report_text(
        f"Submitting payload={args.input_value} to Globus endpoint {args.endpoint_id}"
    )

    my_config = {"account": "datascience"}

    with Executor(endpoint_id=args.endpoint_id, user_endpoint_config=my_config) as executor:
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
