from __future__ import print_function

import argparse
import json
import os
import re
import shlex
import subprocess
import time


def _env(name, default=None):
    value = os.environ.get(name)
    return value if value is not None else default


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "y")

def _env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value is not None else default

def _is_uuid(value):
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", value))

def _resolve_collection_id(name_or_id):
    if _is_uuid(name_or_id):
        return name_or_id
    result = subprocess.run(
        ["globus", "collection", "search", name_or_id, "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "No such command 'search'" in result.stderr:
        result = subprocess.run(
            ["globus", "endpoint", "search", name_or_id, "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError("Failed to resolve collection name: {}".format(name_or_id))
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse collection search output.")

    matches = []
    for item in data.get("DATA", []):
        display = item.get("display_name")
        if display and display.lower() == name_or_id.lower():
            matches.append(item)
    if len(matches) == 1:
        return matches[0].get("id")
    if len(matches) > 1:
        names = [m.get("display_name") for m in matches]
        raise RuntimeError("Multiple collections match '{}': {}".format(name_or_id, names))

    if data.get("DATA"):
        return data["DATA"][0].get("id")
    raise RuntimeError("No collections found for '{}'".format(name_or_id))

def _build_command(args):
    src_endpoint = _resolve_collection_id(args.src_endpoint)
    dst_endpoint = _resolve_collection_id(args.dst_endpoint)
    cmd = ["globus", "transfer", "--label", args.label]
    if args.recursive:
        cmd.append("--recursive")
    if args.sync_level:
        cmd += ["--sync-level", args.sync_level]

    cmd += [f"{src_endpoint}:{args.src_path}", f"{dst_endpoint}:{args.dst_path}"]
    return cmd


def _maybe_log(message):
    try:
        from clearml import Logger
    except Exception:
        return
    Logger.current_logger().report_text(message)

def _maybe_report_scalar(title, series, value, iteration):
    try:
        from clearml import Logger
    except Exception:
        return
    Logger.current_logger().report_scalar(title, series, iteration=iteration, value=value)


def _poll_progress(task_id, interval_s):
    start = time.time()
    last_state = None
    while True:
        result = subprocess.run(
            ["globus", "task", "show", task_id, "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _maybe_log("Failed to query Globus task status; stopping progress polling.")
            return
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            _maybe_log("Failed to parse Globus task status; stopping progress polling.")
            return

        status = data.get("status")
        bytes_transferred = data.get("bytes_transferred", 0)
        bytes_total = data.get("bytes", 0)
        files_transferred = data.get("files_transferred", 0)
        files_total = data.get("files", 0)
        elapsed = max(time.time() - start, 1e-9)

        mb_s = (bytes_transferred / (1024 * 1024)) / elapsed
        _maybe_report_scalar("globus_transfer", "bytes_transferred", bytes_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "bytes_total", bytes_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_transferred", files_transferred, int(elapsed))
        _maybe_report_scalar("globus_transfer", "files_total", files_total, int(elapsed))
        _maybe_report_scalar("globus_transfer", "mb_s", mb_s, int(elapsed))

        if status != last_state:
            _maybe_log("Globus task status: {}".format(status))
            last_state = status

        if status in ("SUCCEEDED", "FAILED", "CANCELED"):
            return
        time.sleep(interval_s)

def main():
    parser = argparse.ArgumentParser(description="Globus data movement task")
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
    args = parser.parse_args()

    if not all([args.src_endpoint, args.dst_endpoint, args.src_path, args.dst_path]):
        raise ValueError(
            "Missing required args: --src-endpoint, --dst-endpoint, --src-path, --dst-path"
        )

    try:
        from clearml import Task
        Task.init(project_name="AmSC", task_name="Globus data movement")
    except Exception:
        pass

    cmd = _build_command(args)
    dry_run = args.dry_run

    _maybe_log("Running Globus transfer command: {}".format(" ".join(map(shlex.quote, cmd))))
    if dry_run:
        print("Dry run:", " ".join(map(shlex.quote, cmd)))
        return

    start = time.time()
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        if result.stderr:
            _maybe_log("Globus transfer stderr: {}".format(result.stderr.strip()))
        _maybe_log("Globus transfer failed with return code {}".format(result.returncode))
        raise SystemExit(result.returncode)

    task_id = None
    if result.stdout:
        for line in result.stdout.splitlines():
            if line.startswith("Task ID:"):
                task_id = line.split(":", 1)[1].strip()
                break
    if task_id:
        if args.no_wait:
            _maybe_log("Globus task submitted; not waiting for completion.")
        else:
            _poll_progress(task_id, args.poll_interval)

    _maybe_log("Globus transfer completed in {:.2f}s".format(elapsed))


if __name__ == "__main__":
    main()
