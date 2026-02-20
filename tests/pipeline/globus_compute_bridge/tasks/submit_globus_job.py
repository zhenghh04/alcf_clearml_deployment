import argparse
import json
import operator
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from clearml import Task
from globus_compute_sdk import Executor
from globus_compute_sdk.serialize import AllCodeStrategies, ComputeSerializer

DEFAULT_ENDPOINT_ID = "fad4d968-8c9a-45ce-9fb4-60a9ab90be60"


def _normalize_optional_str(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null"}:
        return ""
    return normalized


def _parse_positive_int(value: str) -> Optional[int]:
    if not value:
        return None
    parsed = int(value)
    if parsed <= 0:
        return None
    return parsed


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
    parser.add_argument("--account", default="")
    parser.add_argument("--scheduler-queue", default="")
    parser.add_argument("--partition", default="")
    parser.add_argument("--num-nodes", type=int, default=0)
    parser.add_argument("--cores-per-node", type=int, default=0)
    parser.add_argument("--walltime", default="")
    parser.add_argument("--endpoint-config-json", default="")
    parser.add_argument("--script", default="")
    parser.add_argument("--script-args-json", default="")
    parser.add_argument("--binary", default="")
    parser.add_argument("--working-directory", default="")
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


def build_endpoint_config(args: argparse.Namespace, task_params: Dict[str, Any]) -> Dict[str, Any]:
    config: Dict[str, Any] = {}

    account = _normalize_optional_str(args.account) or _normalize_optional_str(
        read_param(task_params, "account")
    )
    scheduler_queue = _normalize_optional_str(args.scheduler_queue) or _normalize_optional_str(
        read_param(task_params, "queue")
    )
    partition = _normalize_optional_str(args.partition) or _normalize_optional_str(
        read_param(task_params, "partition")
    )
    num_nodes_raw = _normalize_optional_str(args.num_nodes) if args.num_nodes else _normalize_optional_str(
        read_param(task_params, "num_nodes")
    )
    cores_per_node_raw = (
        _normalize_optional_str(args.cores_per_node)
        if args.cores_per_node
        else _normalize_optional_str(read_param(task_params, "cores_per_node"))
    )
    walltime = _normalize_optional_str(args.walltime) or _normalize_optional_str(
        read_param(task_params, "walltime")
    )

    if account:
        config["account"] = account
    if scheduler_queue:
        config["queue"] = scheduler_queue
    if partition:
        config["partition"] = partition
    num_nodes = _parse_positive_int(num_nodes_raw)
    cores_per_node = _parse_positive_int(cores_per_node_raw)
    if num_nodes is not None:
        config["num_nodes"] = num_nodes
    if cores_per_node is not None:
        config["cores_per_node"] = cores_per_node
    if walltime:
        config["walltime"] = walltime

    if args.endpoint_config_json:
        config.update(json.loads(args.endpoint_config_json))

    return config


def parse_script_args(args: argparse.Namespace) -> List[str]:
    if not args.script_args_json:
        return []
    parsed = json.loads(args.script_args_json)
    if not isinstance(parsed, list):
        raise ValueError("script-args-json must be a JSON list")
    return [str(item) for item in parsed]


def run_script(
    script_path: str,
    script_args: List[str],
    binary: str,
    working_directory: Optional[str],
) -> Dict[str, Any]:
    cmd = [binary, script_path] + script_args
    completed = subprocess.run(
        cmd,
        cwd=working_directory or None,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "mode": "remote_script",
        "command": cmd,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


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
    logger.report_text(f"Submitting work to Globus endpoint {endpoint_id}")

    endpoint_config = build_endpoint_config(args, task_params)
    if endpoint_config:
        logger.report_text(f"Using endpoint config: {endpoint_config}")
    script = _normalize_optional_str(args.script) or _normalize_optional_str(read_param(task_params, "script"))
    binary = _normalize_optional_str(args.binary) or _normalize_optional_str(
        read_param(task_params, "binary")
    ) or "/bin/bash"
    script_working_directory = _normalize_optional_str(args.working_directory) or _normalize_optional_str(
        read_param(task_params, "working_directory")
    )
    script_args = parse_script_args(args)

    with Executor(
        endpoint_id=endpoint_id,
        user_endpoint_config=endpoint_config or None,
    ) as executor:
        # Avoid dill bytecode compatibility issues across local and endpoint Python versions.
        executor.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
        if script:
            logger.report_text(
                f"Executing script via Globus: binary={binary} script={script}"
            )
            future = executor.submit(
                run_script,
                script,
                script_args,
                binary,
                script_working_directory or None,
            )
        else:
            logger.report_text(f"Executing default multiply payload={args.input_value}")
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

    if script:
        result = {
            "script": script,
            "script_args": script_args,
            "remote_result": output_value,
            "message": "Executed script on Globus Compute endpoint",
        }
        logger.report_scalar(
            "globus_bridge",
            "return_code",
            value=float(output_value.get("return_code", -1)),
            iteration=0,
        )
        if output_value.get("return_code", 1) != 0:
            raise RuntimeError(
                f"Remote script failed with return code {output_value.get('return_code')}: "
                f"{output_value.get('stderr', '')}"
            )
    else:
        result = {
            "input": args.input_value,
            "output": output_value,
            "message": "Executed on Globus Compute endpoint",
        }
        logger.report_scalar("globus_bridge", "output", value=result["output"], iteration=0)

    elapsed = time.time() - start
    logger.report_scalar("globus_bridge", "total_time_sec", value=elapsed, iteration=0)

    artifact_path = Path(args.artifact_path)
    artifact_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    task.upload_artifact(name="globus_result", artifact_object=str(artifact_path))
    logger.report_text(f"Completed Globus Compute execution: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
