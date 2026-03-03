from __future__ import print_function

import argparse
import json
import logging
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
        # Fallback: try endpoint search without json formatting and parse UUID
        fallback = subprocess.run(
            ["globus", "endpoint", "search", name_or_id],
            check=False,
            capture_output=True,
            text=True,
        )
        if fallback.returncode == 0 and fallback.stdout:
            for line in fallback.stdout.splitlines():
                parts = line.split("|")
                if parts and _is_uuid(parts[0].strip()):
                    return parts[0].strip()
            for line in fallback.stdout.splitlines():
                token = line.strip().split()[0] if line.strip() else ""
                if _is_uuid(token):
                    return token
        raise RuntimeError(
            "Failed to resolve collection name: {} (stderr: {})".format(
                name_or_id, (result.stderr or "").strip()
            )
        )
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


def _log(message):
    logging.info(message)


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
            _log("Failed to query Globus task status; stopping progress polling.")
            return
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            _log("Failed to parse Globus task status; stopping progress polling.")
            return

        status = data.get("status")
        bytes_transferred = data.get("bytes_transferred", 0)
        bytes_total = data.get("bytes", 0)
        files_transferred = data.get("files_transferred", 0)
        files_total = data.get("files", 0)
        elapsed = max(time.time() - start, 1e-9)

        mb_s = (bytes_transferred / (1024 * 1024)) / elapsed
        _log(
            "Progress: status=%s bytes=%s/%s files=%s/%s mb_s=%.2f"
            % (status, bytes_transferred, bytes_total, files_transferred, files_total, mb_s)
        )

        if status != last_state:
            _log("Globus task status: {}".format(status))
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

    cmd = _build_command(args)
    dry_run = args.dry_run

    _log("Running Globus transfer command: {}".format(" ".join(map(shlex.quote, cmd))))
    if dry_run:
        print("Dry run:", " ".join(map(shlex.quote, cmd)))
        return

    start = time.time()
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        if result.stderr:
            _log("Globus transfer stderr: {}".format(result.stderr.strip()))
        _log("Globus transfer failed with return code {}".format(result.returncode))
        raise SystemExit(result.returncode)

    task_id = None
    if result.stdout:
        for line in result.stdout.splitlines():
            if line.startswith("Task ID:"):
                task_id = line.split(":", 1)[1].strip()
                break
    if task_id:
        if args.no_wait:
            _log("Globus task submitted; not waiting for completion.")
        else:
            _poll_progress(task_id, args.poll_interval)

    _log("Globus transfer completed in {:.2f}s".format(elapsed))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
