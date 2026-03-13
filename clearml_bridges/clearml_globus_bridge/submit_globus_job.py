import argparse
import json
import operator
import os
import time
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

from globus_compute_sdk import Executor
from globus_compute_sdk.serialize import AllCodeStrategies, ComputeSerializer

MIN_GLOBUS_SDK = (3, 59, 0)
MIN_GLOBUS_COMPUTE_SDK = (4, 6, 0)

def clean_str(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null"}:
        return ""
    return normalized


def parse_bool(value: Any, default: bool = False) -> bool:
    normalized = clean_str(value).lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on"}


def parse_version_tuple(raw: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in raw.replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def ensure_runtime_packages() -> None:
    required = [
        ("globus-sdk", MIN_GLOBUS_SDK),
        ("globus-compute-sdk", MIN_GLOBUS_COMPUTE_SDK),
    ]
    problems: list[str] = []
    for package_name, min_version in required:
        try:
            installed = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            problems.append(f"{package_name} is not installed")
            continue
        if parse_version_tuple(installed) < min_version:
            problems.append(
                f"{package_name}=={installed} is too old; need >= {'.'.join(map(str, min_version))}"
            )
    if problems:
        raise RuntimeError(
            "Incompatible Globus runtime packages detected:\n"
            + "\n".join(f"- {item}" for item in problems)
            + "\nFix with:\n"
            + '  python -m pip install --upgrade "globus-sdk>=3.59.0,<4" "globus-compute-sdk>=4.6.0"'
        )


def collect_debug_env_snapshot() -> Dict[str, str]:
    snapshot = {"python_executable": os.sys.executable}
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    ):
        snapshot[key] = os.getenv(key, "")
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-name", "--project_name",
        default=os.getenv("CLEARML_PROJECT_NAME", "amsc/pipeline-globus-bridge"),
    )
    parser.add_argument(
        "--task-name", "--task_name",
        default=os.getenv("CLEARML_TASK_NAME", "submit-globus-compute-job"),
    )
    parser.add_argument(
        "--task-type", "--task_type",
        default=os.getenv("CLEARML_TASK_TYPE", "data_processing"),
    )
    parser.add_argument(
        "--endpoint-id", "--endpoint_id",
        default=os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID", ""),
    )
    parser.add_argument(
        "--endpoint-name", "--endpoint_name",
        default=os.getenv("GLOBUS_COMPUTE_ENDPOINT_NAME", ""),
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GLOBUS_COMPUTE_ACCESS_TOKEN", ""),
        help=(
            "Globus access token for non-interactive auth. "
            "If omitted, default SDK auth flow is used."
        ),
    )
    parser.add_argument("--input-value", "--input_value", type=int, default=7)
    parser.add_argument("--poll-interval", "--poll_interval", type=int, default=5)
    parser.add_argument("--timeout-sec", "--timeout_sec", type=int, default=900)
    parser.add_argument(
        "--report-wait-metrics", "--report_wait_metrics",
        default=os.getenv("GLOBUS_REPORT_WAIT_METRICS", "0"),
        help="Enable per-poll wait metric reporting to ClearML (default: disabled).",
    )
    parser.add_argument("--artifact-path", "--artifact_path", default="globus_result.json")
    parser.add_argument("--endpoint-config-json", "--endpoint_config_json", default="")
    parser.add_argument("--script", default="")
    parser.add_argument("--script-args-json", "--script_args_json", default="")
    parser.add_argument("--binary", default="")
    parser.add_argument("--working-directory", "--working_directory", default="")
    parser.add_argument("--repo-url", "--repo_url", default="")
    parser.add_argument("--repo-branch", "--repo_branch", default="")
    parser.add_argument("--repo-working-directory", "--repo_working_directory", default="")
    parser.add_argument("--clone-repo", "--clone_repo", default="")
    parser.add_argument(
        "--submit-retries", "--submit_retries",
        type=int,
        default=int(os.getenv("GLOBUS_SUBMIT_RETRIES", "2")),
        help="Retry count for transient submission failures (default: 2).",
    )
    parser.add_argument(
        "--retry-backoff-sec", "--retry_backoff_sec",
        type=int,
        default=int(os.getenv("GLOBUS_RETRY_BACKOFF_SEC", "5")),
        help="Base backoff in seconds between submit retries (default: 5).",
    )
    parser.add_argument(
        "--required-endpoint-keys", "--required_endpoint_keys",
        default=os.getenv("GLOBUS_REQUIRED_ENDPOINT_KEYS", ""),
        help="Comma-separated required keys in endpoint config (example: filesystems).",
    )
    parser.add_argument(
        "--debug-env", "--debug_env",
        default=os.getenv("GLOBUS_DEBUG_ENV", "0"),
        help="Log Python executable and proxy-related environment variables at startup.",
    )
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


def read_user_property(user_properties: Dict[str, Any], name: str) -> str:
    candidates = [
        name,
        name.replace("_", "-"),
        name.replace("-", "_"),
    ]
    for candidate in candidates:
        value = user_properties.get(candidate)
        normalized = clean_str(value)
        if normalized:
            return normalized
    return ""


def coerce_user_property_value(value: Any) -> Any:
    normalized = clean_str(value)
    if not normalized:
        return ""
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return ""
    if normalized.startswith("{") or normalized.startswith("["):
        try:
            return json.loads(normalized)
        except Exception:
            pass
    try:
        return int(normalized)
    except Exception:
        pass
    try:
        return float(normalized)
    except Exception:
        pass
    return normalized


def build_endpoint_config(
    args: argparse.Namespace,
    task_params: Dict[str, Any],
    task_user_properties: Dict[str, Any],
) -> Dict[str, Any]:
    config: Dict[str, Any] = {}

    endpoint_config_json = (
        clean_str(args.endpoint_config_json)
        or read_user_property(task_user_properties, "endpoint_config_json")
        or clean_str(read_param(task_params, "endpoint_config_json"))
    )
    if endpoint_config_json:
        config.update(json.loads(endpoint_config_json))

    reserved_keys = {
        "endpoint_config_json",
    }
    for key, raw_value in task_user_properties.items():
        canonical_key = str(key).strip().replace("-", "_")
        if not canonical_key or canonical_key in reserved_keys:
            continue
        parsed_value = coerce_user_property_value(raw_value)
        if parsed_value == "":
            continue
        config[canonical_key] = parsed_value

    return config


def build_compute_client(access_token: str = "") -> Any:
    try:
        from globus_compute_sdk import Client
    except ImportError as exc:
        raise RuntimeError(
            "Incompatible Globus package versions detected for Compute SDK.\n"
            f"Original error: {exc}\n"
            "Fix with:\n"
            "  python -m pip install --upgrade \"globus-sdk>=3.59.0,<4\" \"globus-compute-sdk>=4.6.0\""
        ) from exc

    token = clean_str(access_token)
    if not token:
        return Client()

    import globus_sdk

    return Client(authorizer=globus_sdk.AccessTokenAuthorizer(token))


def resolve_endpoint_id_from_name(endpoint_name: str, access_token: str = "") -> str:
    normalized_name = clean_str(endpoint_name)
    if not normalized_name:
        return ""

    client = build_compute_client(access_token)
    endpoints = client.get_endpoints(role="any") or []

    def endpoint_name_of(item: Dict[str, Any]) -> str:
        return clean_str(
            item.get("display_name")
            or item.get("name")
            or item.get("endpoint_name")
        )

    def endpoint_id_of(item: Dict[str, Any]) -> str:
        return clean_str(
            item.get("uuid")
            or item.get("id")
            or item.get("endpoint_id")
        )

    exact_matches = [
        endpoint_id_of(item)
        for item in endpoints
        if endpoint_name_of(item) == normalized_name and endpoint_id_of(item)
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(
            f"Multiple endpoints found for name '{normalized_name}'. "
            f"Please pass --endpoint-id explicitly."
        )

    partial_matches = [
        endpoint_id_of(item)
        for item in endpoints
        if normalized_name.lower() in endpoint_name_of(item).lower() and endpoint_id_of(item)
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if len(partial_matches) > 1:
        raise ValueError(
            f"Multiple endpoint partial matches found for '{normalized_name}'. "
            f"Please pass --endpoint-id explicitly."
        )
    raise ValueError(
        f"No endpoint found with name '{normalized_name}'. "
        "Check endpoint name or pass --endpoint-id."
    )


def resolve_endpoint_name_from_id(endpoint_id: str, access_token: str = "") -> str:
    normalized_id = clean_str(endpoint_id)
    if not normalized_id:
        return ""

    client = build_compute_client(access_token)
    metadata = client.get_endpoint_metadata(normalized_id) or {}
    return clean_str(
        metadata.get("display_name")
        or metadata.get("name")
        or metadata.get("endpoint_name")
    )


def parse_script_args(args: argparse.Namespace) -> List[str]:
    if not args.script_args_json:
        return []
    parsed = json.loads(args.script_args_json)
    if not isinstance(parsed, list):
        raise ValueError("script-args-json must be a JSON list")
    return [str(item) for item in parsed]


def preview_text(text: str, max_lines: int = 20) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    head = "\n".join(lines[:max_lines])
    return f"{head}\n... ({len(lines) - max_lines} more lines)"


def parse_required_keys(raw: str) -> List[str]:
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def validate_endpoint_config(config: Dict[str, Any], required_keys: List[str]) -> None:
    if not required_keys:
        return
    missing = [k for k in required_keys if k not in config or config.get(k) in (None, "")]
    if missing:
        raise ValueError(
            "Missing required endpoint config keys: "
            f"{missing}. Current config: {config}"
        )


def is_retryable_submission_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retry_tokens = [
        "endpoint_not_online",
        "disconnected",
        "connection closed",
        "connection broken",
        "incompleteread",
        "incomplete read",
        "protocolerror",
        "protocol error",
        "chunkedencodingerror",
        "chunked encoding error",
        "temporarily unavailable",
        "timed out",
        "timeout",
    ]
    non_retry_tokens = [
        "access_refused",
        "invalid credentials",
        "authentication",
        "resource: filesystems is required",
        "resource_conflict",
    ]
    if any(t in msg for t in non_retry_tokens):
        return False
    return any(t in msg for t in retry_tokens)


def call_with_retries(
    func: Any,
    *func_args: Any,
    retries: int,
    retry_backoff_sec: int,
    logger: Any = None,
    action_name: str = "operation",
    **func_kwargs: Any,
) -> Any:
    max_attempts = max(1, retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*func_args, **func_kwargs)
        except Exception as exc:
            if attempt >= max_attempts or not is_retryable_submission_error(exc):
                raise
            sleep_sec = retry_backoff_sec * attempt
            if logger is not None:
                logger.report_text(
                    f"{action_name} attempt {attempt}/{max_attempts} failed with retryable error: {exc}\n"
                    f"Retrying in {sleep_sec}s..."
                )
            time.sleep(sleep_sec)


def run_script(
    script_path: str,
    script_args: List[str],
    binary: str,
    working_directory: Optional[str],
    repo_url: Optional[str],
    repo_branch: Optional[str],
    repo_working_directory: Optional[str],
    clone_repo: bool,
) -> Dict[str, Any]:
    # Keep imports inside the remotely executed function to avoid missing globals
    # when deserialized on endpoint workers with different Python environments.
    import os
    import subprocess
    import tempfile

    checkout_root = ""
    run_cwd = working_directory or None
    resolved_script_path = script_path

    if clone_repo:
        if not repo_url:
            raise ValueError("clone_repo is enabled but repo_url is empty")
        checkout_root = tempfile.mkdtemp(prefix="globus_repo_")
        clone_cmd = ["git", "clone", "--depth", "1", repo_url, checkout_root]
        if repo_branch:
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", repo_branch, repo_url, checkout_root]
        clone_completed = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if clone_completed.returncode != 0:
            return {
                "mode": "remote_script",
                "clone_repo": True,
                "repo_url": repo_url,
                "repo_branch": repo_branch,
                "clone_command": clone_cmd,
                "return_code": clone_completed.returncode,
                "stdout": clone_completed.stdout,
                "stderr": clone_completed.stderr,
            }

        run_cwd = checkout_root
        if repo_working_directory:
            repo_rel_dir = repo_working_directory.lstrip("./")
            run_cwd = os.path.join(checkout_root, repo_rel_dir)
        resolved_script_path = (
            script_path
            if os.path.isabs(script_path)
            else os.path.join(checkout_root, script_path.lstrip("./"))
        )
    elif run_cwd and not os.path.isabs(script_path):
        resolved_script_path = os.path.join(run_cwd, script_path.lstrip("./"))

    cmd = [binary, resolved_script_path] + script_args
    completed = subprocess.run(
        cmd,
        cwd=run_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "mode": "remote_script",
        "command": cmd,
        "clone_repo": clone_repo,
        "repo_url": repo_url,
        "repo_branch": repo_branch,
        "repo_working_directory": repo_working_directory,
        "resolved_script_path": resolved_script_path,
        "cwd": run_cwd,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def resolve_task_type(TaskCls: Any, task_type_name: str) -> Any:
    normalized = clean_str(task_type_name)
    if not normalized:
        return TaskCls.TaskTypes.data_processing
    for task_type in TaskCls.TaskTypes:
        value = clean_str(getattr(task_type, "value", ""))
        name = clean_str(getattr(task_type, "name", ""))
        if normalized == value or normalized == name.lower():
            return task_type
    raise ValueError(
        f"Unsupported task type '{task_type_name}'. "
        f"Supported values: {[getattr(t, 'value', str(t)) for t in TaskCls.TaskTypes]}"
    )


def main() -> int:
    args = parse_args()
    ensure_runtime_packages()
    from clearml import Task

    initial_params = vars(args).copy()
    if clean_str(initial_params.get("token")):
        initial_params["token"] = "***"
    project_name = clean_str(args.project_name) or "amsc/pipeline-globus-bridge"
    task_name = clean_str(args.task_name) or "submit-globus-compute-job"
    task_type = resolve_task_type(Task, args.task_type)

    task = Task.init(
        project_name=project_name,
        task_name=task_name,
        task_type=task_type,
    )
    task.connect(initial_params, name="bridge")
    logger = task.get_logger()
    if parse_bool(args.debug_env, default=False):
        logger.report_text(
            "Worker environment snapshot:\n"
            + json.dumps(collect_debug_env_snapshot(), indent=2, sort_keys=True)
        )

    task_params = task.get_parameters_as_dict(cast=True)
    task_user_properties = task.get_user_properties(value_only=True)
    access_token = clean_str(args.token)
    endpoint_id = (
        clean_str(args.endpoint_id)
        or clean_str(read_param(task_params, "endpoint_id"))
    )
    endpoint_name = (
        clean_str(args.endpoint_name)
        or clean_str(read_param(task_params, "endpoint_name"))
    )
    if not endpoint_id and endpoint_name:
        endpoint_id = call_with_retries(
            resolve_endpoint_id_from_name,
            endpoint_name,
            access_token=access_token,
            retries=args.submit_retries,
            retry_backoff_sec=args.retry_backoff_sec,
            logger=logger,
            action_name="Endpoint name resolution",
        )
    if not endpoint_name and endpoint_id:
        try:
            endpoint_name = call_with_retries(
                resolve_endpoint_name_from_id,
                endpoint_id,
                access_token=access_token,
                retries=args.submit_retries,
                retry_backoff_sec=args.retry_backoff_sec,
                logger=logger,
                action_name="Endpoint metadata lookup",
            )
        except Exception:
            endpoint_name = ""
    if not endpoint_id:
        logger.report_text(f"Parameter keys visible to task: {sorted(flatten_params(task_params).keys())}")
        raise ValueError(
            "Endpoint is required. Set --endpoint-id or --endpoint-name "
            "(or env GLOBUS_COMPUTE_ENDPOINT_ID / GLOBUS_COMPUTE_ENDPOINT_NAME)."
        )

    start = time.time()
    logger.report_text(
        "ClearML task context: "
        f"project={project_name} task={task_name} task_type={clean_str(args.task_type) or 'data_processing'}"
    )
    logger.report_text(
        "Submitting work to Globus endpoint "
        f"name={endpoint_name or '<unknown>'} id={endpoint_id}"
    )
    if access_token:
        logger.report_text("Using token-based Globus Compute client authentication.")

    endpoint_config = build_endpoint_config(args, task_params, task_user_properties)
    if endpoint_config:
        logger.report_text(f"Using endpoint config: {endpoint_config}")
    script = clean_str(args.script) or clean_str(read_param(task_params, "script"))
    binary = clean_str(args.binary) or clean_str(
        read_param(task_params, "binary")
    ) or "/bin/bash"
    script_working_directory = clean_str(args.working_directory) or clean_str(
        read_param(task_params, "working_directory")
    )
    repo_url = clean_str(args.repo_url) or clean_str(read_param(task_params, "repo_url"))
    repo_branch = clean_str(args.repo_branch) or clean_str(
        read_param(task_params, "repo_branch")
    )
    repo_working_directory = clean_str(args.repo_working_directory) or clean_str(
        read_param(task_params, "repo_working_directory")
    )
    clone_repo = parse_bool(args.clone_repo or read_param(task_params, "clone_repo"), default=False)
    script_args = parse_script_args(args)

    required_keys = parse_required_keys(args.required_endpoint_keys)
    validate_endpoint_config(endpoint_config, required_keys)

    output_value: Any = None
    compute_client = build_compute_client(access_token)
    max_attempts = max(1, args.submit_retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            with Executor(
                endpoint_id=endpoint_id,
                client=compute_client,
                user_endpoint_config=endpoint_config or None,
            ) as executor:
                # Avoid dill bytecode compatibility issues across local and endpoint Python versions.
                executor.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
                if script:
                    logger.report_text(
                        f"Executing script via Globus: binary={binary} script={script}"
                    )
                    if clone_repo:
                        logger.report_text(
                            f"clone_repo enabled: repo={repo_url} branch={repo_branch or 'default'} "
                            f"repo_working_directory={repo_working_directory or '.'}"
                        )
                    future = executor.submit(
                        run_script,
                        script,
                        script_args,
                        binary,
                        script_working_directory or None,
                        repo_url or None,
                        repo_branch or None,
                        repo_working_directory or None,
                        clone_repo,
                    )
                else:
                    logger.report_text(f"Executing default multiply payload={args.input_value}")
                    # Use stdlib callable to avoid Python minor-version bytecode mismatch issues.
                    future = executor.submit(operator.mul, args.input_value, args.input_value)
                while not future.done():
                    elapsed = time.time() - start
                    if parse_bool(args.report_wait_metrics, default=False):
                        try:
                            logger.report_scalar(
                                "globus_bridge", "wait_time_sec", value=elapsed, iteration=int(elapsed)
                            )
                        except RuntimeError:
                            # ClearML monitor thread can fail under tight thread limits.
                            pass
                    if elapsed > args.timeout_sec:
                        raise TimeoutError(
                            f"Timed out waiting for Globus task after {args.timeout_sec}s"
                        )
                    time.sleep(args.poll_interval)
                output_value = future.result()
            break
        except Exception as exc:
            if attempt >= max_attempts or not is_retryable_submission_error(exc):
                raise
            sleep_sec = args.retry_backoff_sec * attempt
            logger.report_text(
                f"Submission attempt {attempt}/{max_attempts} failed with retryable error: {exc}\n"
                f"Retrying in {sleep_sec}s..."
            )
            time.sleep(sleep_sec)

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
    if script:
        remote_result = result.get("remote_result", {}) if isinstance(result, dict) else {}
        stdout_text = str(remote_result.get("stdout", ""))
        stderr_text = str(remote_result.get("stderr", ""))

        stdout_path = Path("globus_stdout.txt")
        stdout_path.write_text(stdout_text, encoding="utf-8")
        task.upload_artifact(name="globus_stdout", artifact_object=str(stdout_path))

        if stderr_text:
            stderr_path = Path("globus_stderr.txt")
            stderr_path.write_text(stderr_text, encoding="utf-8")
            task.upload_artifact(name="globus_stderr", artifact_object=str(stderr_path))

        logger.report_text(
            "Completed Globus Compute execution:\n"
            f"- mode: script\n"
            f"- command: {remote_result.get('command')}\n"
            f"- return_code: {remote_result.get('return_code')}\n"
            f"- cwd: {remote_result.get('cwd')}\n"
            f"- resolved_script_path: {remote_result.get('resolved_script_path')}\n"
            f"- elapsed_sec: {elapsed:.2f}\n"
            f"- stdout_preview:\n{preview_text(stdout_text)}"
        )
    else:
        logger.report_text(
            "Completed Globus Compute execution:\n"
            "- mode: default_multiply\n"
            f"- input: {result.get('input')}\n"
            f"- output: {result.get('output')}\n"
            f"- elapsed_sec: {elapsed:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
