import argparse
import json
import os
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    return value if value is not None else default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "y")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value is not None else default


def _is_uuid(value: str) -> bool:
    return bool(
        re.match(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            value,
        )
    )


def _run_json_cmd(cmd: List[str]) -> Dict[str, Any]:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(map(shlex.quote, cmd))}\n"
            f"stderr: {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON from command: {' '.join(cmd)}") from exc


def _resolve_collection_id(name_or_id: str) -> str:
    if _is_uuid(name_or_id):
        return name_or_id

    cmd = ["globus", "collection", "search", name_or_id, "--format", "json"]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0 and "No such command 'search'" in result.stderr:
        cmd = ["globus", "endpoint", "search", name_or_id, "--format", "json"]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to resolve collection name: {name_or_id}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse collection search output.") from exc

    exact_matches = []
    for item in data.get("DATA", []):
        display = item.get("display_name")
        if display and display.lower() == name_or_id.lower():
            exact_matches.append(item)
    if len(exact_matches) == 1:
        return str(exact_matches[0].get("id"))
    if len(exact_matches) > 1:
        names = [m.get("display_name") for m in exact_matches]
        raise RuntimeError(f"Multiple collections match '{name_or_id}': {names}")
    if data.get("DATA"):
        return str(data["DATA"][0].get("id"))
    raise RuntimeError(f"No collections found for '{name_or_id}'")


def _resolve_collection_id_with_sdk(client: Any, name_or_id: str) -> str:
    if _is_uuid(name_or_id):
        return name_or_id

    try:
        result = client.endpoint_search(name_or_id)
        data = result.data if hasattr(result, "data") else {}
    except Exception as exc:
        raise RuntimeError(f"Failed to resolve collection name via SDK: {name_or_id}") from exc

    items = data.get("DATA", []) if isinstance(data, dict) else []
    exact_matches = []
    for item in items:
        display = item.get("display_name")
        if display and str(display).lower() == name_or_id.lower():
            exact_matches.append(item)
    if len(exact_matches) == 1:
        return str(exact_matches[0].get("id"))
    if len(exact_matches) > 1:
        names = [m.get("display_name") for m in exact_matches]
        raise RuntimeError(f"Multiple collections match '{name_or_id}': {names}")
    if items:
        return str(items[0].get("id"))
    raise RuntimeError(f"No collections found for '{name_or_id}'")


def _maybe_log(message: str) -> None:
    try:
        from clearml import Logger
    except Exception:
        return
    Logger.current_logger().report_text(message)


def _maybe_report_scalar(title: str, series: str, value: float, iteration: int) -> None:
    try:
        from clearml import Logger
    except Exception:
        return
    Logger.current_logger().report_scalar(title, series, iteration=iteration, value=value)


def _build_transfer_command(args: argparse.Namespace) -> List[str]:
    src_endpoint = _resolve_collection_id(args.src_endpoint)
    dst_endpoint = _resolve_collection_id(args.dst_endpoint)
    cmd = ["globus", "transfer", "--label", args.label, "--format", "json"]
    if args.recursive:
        cmd.append("--recursive")
    if args.sync_level:
        cmd += ["--sync-level", args.sync_level]
    cmd += [f"{src_endpoint}:{args.src_path}", f"{dst_endpoint}:{args.dst_path}"]
    return cmd


def _submit_transfer_with_sdk(args: argparse.Namespace, access_token: str) -> str:
    import globus_sdk

    authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
    transfer_client = globus_sdk.TransferClient(authorizer=authorizer)
    src_endpoint = _resolve_collection_id_with_sdk(transfer_client, args.src_endpoint)
    dst_endpoint = _resolve_collection_id_with_sdk(transfer_client, args.dst_endpoint)

    transfer_data = globus_sdk.TransferData(
        transfer_client,
        source_endpoint=src_endpoint,
        destination_endpoint=dst_endpoint,
        label=args.label,
        sync_level=args.sync_level or None,
    )
    transfer_data.add_item(args.src_path, args.dst_path, recursive=args.recursive)
    response = transfer_client.submit_transfer(transfer_data)
    return str(response["task_id"])


def _poll_transfer_with_sdk(task_id: str, poll_interval: int, access_token: str) -> str:
    import globus_sdk

    authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
    transfer_client = globus_sdk.TransferClient(authorizer=authorizer)
    start = time.time()
    last_status = ""
    final_status = ""
    while True:
        try:
            data = transfer_client.get_task(task_id).data
        except Exception as exc:
            _maybe_log(f"Failed to query Globus task status: {exc}")
            return final_status or "UNKNOWN"

        status = str(data.get("status", "")).upper()
        bytes_transferred = float(data.get("bytes_transferred", 0) or 0)
        bytes_total = float(data.get("bytes", 0) or 0)
        files_transferred = float(data.get("files_transferred", 0) or 0)
        files_total = float(data.get("files", 0) or 0)
        elapsed = max(time.time() - start, 1e-9)
        mb_s = (bytes_transferred / (1024 * 1024)) / elapsed

        _maybe_report_scalar("globus_transfer", "bytes_transferred", bytes_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "bytes_total", bytes_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_transferred", files_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_total", files_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "mb_s", mb_s, int(elapsed))

        if status != last_status:
            _maybe_log(f"Globus task status: {status}")
            last_status = status
        final_status = status
        if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return status
        time.sleep(poll_interval)


def _extract_task_id(stdout: str) -> str:
    if not stdout:
        return ""
    try:
        parsed = json.loads(stdout)
        task_id = parsed.get("task_id") or parsed.get("DATA", {}).get("task_id")
        if task_id:
            return str(task_id)
    except json.JSONDecodeError:
        pass
    for line in stdout.splitlines():
        if line.startswith("Task ID:"):
            return line.split(":", 1)[1].strip()
    return ""


def _poll_transfer(task_id: str, poll_interval: int) -> str:
    start = time.time()
    last_status = ""
    final_status = ""
    while True:
        try:
            data = _run_json_cmd(["globus", "task", "show", task_id, "--format", "json"])
        except Exception as exc:
            _maybe_log(f"Failed to query Globus task status: {exc}")
            return final_status or "UNKNOWN"

        status = str(data.get("status", "")).upper()
        bytes_transferred = float(data.get("bytes_transferred", 0) or 0)
        bytes_total = float(data.get("bytes", 0) or 0)
        files_transferred = float(data.get("files_transferred", 0) or 0)
        files_total = float(data.get("files", 0) or 0)
        elapsed = max(time.time() - start, 1e-9)
        mb_s = (bytes_transferred / (1024 * 1024)) / elapsed

        _maybe_report_scalar("globus_transfer", "bytes_transferred", bytes_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "bytes_total", bytes_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_transferred", files_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_total", files_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "mb_s", mb_s, int(elapsed))

        if status != last_status:
            _maybe_log(f"Globus task status: {status}")
            last_status = status
        final_status = status
        if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return status
        time.sleep(poll_interval)


def _parse_transfer_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Globus Transfer for data movement.")
    parser.add_argument("--src-endpoint", default=_env("GLOBUS_SRC_ENDPOINT"))
    parser.add_argument("--dst-endpoint", default=_env("GLOBUS_DST_ENDPOINT"))
    parser.add_argument("--src-path", default=_env("GLOBUS_SRC_PATH"))
    parser.add_argument("--dst-path", default=_env("GLOBUS_DST_PATH"))
    parser.add_argument("--label", default=_env("GLOBUS_LABEL", "clearml-data-movement"))
    parser.add_argument("--recursive", action="store_true", default=_env_bool("GLOBUS_RECURSIVE", False))
    parser.add_argument("--sync-level", default=_env("GLOBUS_SYNC_LEVEL"))
    parser.add_argument("--poll-interval", type=int, default=_env_int("GLOBUS_POLL_INTERVAL", 10))
    parser.add_argument("--no-wait", action="store_true", default=_env_bool("GLOBUS_NO_WAIT", False))
    parser.add_argument("--dry-run", action="store_true", default=_env_bool("GLOBUS_DRY_RUN", False))
    parser.add_argument(
        "--token",
        default=_env("GLOBUS_TRANSFER_ACCESS_TOKEN", _env("GLOBUS_ACCESS_TOKEN", "")),
        help="Globus Transfer access token; when set, transfer uses SDK auth instead of CLI login state.",
    )
    parser.add_argument("--project-name", default=_env("CLEARML_PROJECT_NAME", "AmSC"))
    parser.add_argument("--task-name", default=_env("CLEARML_TASK_NAME", "Globus data movement"))
    return parser.parse_args()


def main() -> int:
    args = _parse_transfer_args()
    if not all([args.src_endpoint, args.dst_endpoint, args.src_path, args.dst_path]):
        raise ValueError(
            "Missing required args: --src-endpoint, --dst-endpoint, --src-path, --dst-path"
        )

    try:
        from clearml import Task

        Task.init(project_name=args.project_name, task_name=args.task_name)
    except Exception:
        pass

    using_token = bool(str(args.token).strip())
    if using_token:
        _maybe_log("Using token-based SDK auth for Globus Transfer.")
    else:
        cmd = _build_transfer_command(args)
        _maybe_log(f"Running Globus transfer command: {' '.join(map(shlex.quote, cmd))}")
    if args.dry_run:
        if using_token:
            print(
                "Dry run (SDK mode): transfer "
                f"{args.src_endpoint}:{args.src_path} -> {args.dst_endpoint}:{args.dst_path}"
            )
        else:
            cmd = _build_transfer_command(args)
            print("Dry run:", " ".join(map(shlex.quote, cmd)))
        return 0

    start = time.time()
    if using_token:
        try:
            task_id = _submit_transfer_with_sdk(args, str(args.token).strip())
        except Exception as exc:
            _maybe_log(f"Globus transfer submit failed in SDK mode: {exc}")
            return 1
    else:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            _maybe_log(f"Globus transfer failed (rc={result.returncode})")
            if result.stderr:
                _maybe_log(f"stderr: {result.stderr.strip()}")
            return result.returncode
        task_id = _extract_task_id(result.stdout)
    status = "SUBMITTED"
    if task_id:
        _maybe_log(f"Globus transfer task id: {task_id}")
        if args.no_wait:
            _maybe_log("Submitted transfer; not waiting for completion.")
        else:
            if using_token:
                status = _poll_transfer_with_sdk(task_id, args.poll_interval, str(args.token).strip())
            else:
                status = _poll_transfer(task_id, args.poll_interval)

    elapsed = time.time() - start
    _maybe_log(f"Globus transfer finished in {elapsed:.2f}s with status={status}")
    if status in {"FAILED", "CANCELED"}:
        return 2
    return 0


def _parse_launch_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and enqueue a ClearML Globus transfer task.")
    parser.add_argument("--src-endpoint", default=_env("GLOBUS_SRC_ENDPOINT"))
    parser.add_argument("--dst-endpoint", default=_env("GLOBUS_DST_ENDPOINT"))
    parser.add_argument("--src-path", default=_env("GLOBUS_SRC_PATH"))
    parser.add_argument("--dst-path", default=_env("GLOBUS_DST_PATH"))
    parser.add_argument("--label", default=_env("GLOBUS_LABEL", "clearml-data-movement"))
    parser.add_argument("--recursive", action="store_true", default=_env_bool("GLOBUS_RECURSIVE", False))
    parser.add_argument("--sync-level", default=_env("GLOBUS_SYNC_LEVEL"))
    parser.add_argument("--poll-interval", type=int, default=_env_int("GLOBUS_POLL_INTERVAL", 10))
    parser.add_argument("--dry-run", action="store_true", default=_env_bool("GLOBUS_DRY_RUN", False))
    parser.add_argument("--no-wait", action="store_true", default=_env_bool("GLOBUS_NO_WAIT", False))
    parser.add_argument(
        "--token",
        default=_env("GLOBUS_TRANSFER_ACCESS_TOKEN", _env("GLOBUS_ACCESS_TOKEN", "")),
        help="Globus Transfer access token passed to worker task.",
    )
    parser.add_argument("--queue", default=_env("QUEUE", "default"))
    parser.add_argument("--project-name", default=_env("CLEARML_PROJECT_NAME", "AmSC"))
    parser.add_argument(
        "--task-name",
        default=_env("CLEARML_TASK_NAME", "Globus data movement (enqueued)"),
    )
    return parser.parse_args()


def launch_main() -> int:
    args = _parse_launch_args()
    if not all([args.src_endpoint, args.dst_endpoint, args.src_path, args.dst_path]):
        raise ValueError(
            "Missing required args: --src-endpoint, --dst-endpoint, --src-path, --dst-path"
        )

    from clearml import Task

    task = Task.create(
        project_name=args.project_name,
        task_name=args.task_name,
        task_type=Task.TaskTypes.data_processing,
        module="clearml_globus_bridge.data_movement",
        packages=["-e ."],
        argparse_args=[
            ("project-name", args.project_name),
            ("task-name", "Globus data movement"),
        ],
    )
    task.set_environment(
        {
            "GLOBUS_SRC_ENDPOINT": args.src_endpoint,
            "GLOBUS_DST_ENDPOINT": args.dst_endpoint,
            "GLOBUS_SRC_PATH": args.src_path,
            "GLOBUS_DST_PATH": args.dst_path,
            "GLOBUS_LABEL": args.label,
            "GLOBUS_RECURSIVE": "1" if args.recursive else "0",
            "GLOBUS_SYNC_LEVEL": args.sync_level or "",
            "GLOBUS_POLL_INTERVAL": str(args.poll_interval),
            "GLOBUS_DRY_RUN": "1" if args.dry_run else "0",
            "GLOBUS_NO_WAIT": "1" if args.no_wait else "0",
            "GLOBUS_TRANSFER_ACCESS_TOKEN": args.token or "",
        }
    )
    Task.enqueue(task, queue_name=args.queue)
    print(f"Enqueued task id={task.id} queue={args.queue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
