import argparse
import errno
import os
import select
import subprocess
import sys
import time
from typing import Any, Dict


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else default


def _run_cmd(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (rc={result.returncode}): {' '.join(cmd)}"
        )


def _flatten_params(params: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in params.items():
        full_key = f"{prefix}/{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_params(value, full_key))
        else:
            flattened[full_key] = value
    return flattened


def _read_param_from_flat(flat: Dict[str, Any], name: str) -> str:
    candidate_suffixes = [
        f"/{name}",
        f"/{name.replace('_', '-')}",
        f"/{name.replace('-', '_')}",
        f"/--{name.replace('_', '-')}",
        f"/env:{name}",
    ]
    for key, value in flat.items():
        for suffix in candidate_suffixes:
            if key.endswith(suffix) and value not in (None, ""):
                return str(value)
    return ""


def _hydrate_auth_code_from_task(args: argparse.Namespace) -> None:
    if str(args.auth_code or "").strip():
        return
    try:
        from clearml import Task

        task = Task.current_task() or Task.get_task(task_id=_env("CLEARML_TASK_ID", ""))
        if task is None:
            return
        params = task.get_parameters_as_dict(cast=True) or {}
    except Exception:
        return

    flat = _flatten_params(params)
    auth_code = (
        _read_param_from_flat(flat, "auth-code")
        or _read_param_from_flat(flat, "auth_code")
        or _read_param_from_flat(flat, "CLEARML_GLOBUS_AUTH_CODE")
    )
    if auth_code:
        args.auth_code = auth_code


def _run_with_pty_and_auth_code(cmd: list[str], auth_code: str) -> int:
    master_fd, slave_fd = os.openpty()
    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    sent_code = False
    started_at = time.time()
    buffer = ""
    try:
        while True:
            if proc.poll() is not None:
                break
            rlist, _, _ = select.select([master_fd], [], [], 0.5)
            if not rlist:
                continue
            try:
                chunk = os.read(master_fd, 4096)
            except OSError as exc:
                # PTY can raise EIO when the slave side is closed; treat as EOF.
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                continue
            text = chunk.decode(errors="replace")
            print(text, end="", flush=True)
            buffer = (buffer + text)[-2000:]
            lowered = buffer.lower()
            if (not sent_code) and (
                ("authorization code" in lowered)
                or ("enter the resulting" in lowered)
                or ("enter code" in lowered)
            ):
                os.write(master_fd, f"{auth_code}\n".encode())
                sent_code = True
            elif (not sent_code) and (time.time() - started_at) > 3:
                # Fallback for CLI variants where prompt text is not emitted in a single chunk.
                os.write(master_fd, f"{auth_code}\n".encode())
                sent_code = True

        # Drain remaining output
        while True:
            try:
                chunk = os.read(master_fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            print(chunk.decode(errors="replace"), end="", flush=True)
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

    return int(proc.returncode or 0)


def _run_transfer_login(auth_code: str) -> bool:
    cmd = ["globus", "login", "--no-local-server"]

    if auth_code:
        rc = _run_with_pty_and_auth_code(cmd, auth_code)
        if rc != 0:
            raise RuntimeError(
                f"Command failed (rc={rc}): {' '.join(cmd)}"
            )
        return True

    if not sys.stdin.isatty():
        # Best effort: force a pseudo-TTY so CLI prints URL in non-interactive agent logs.
        pty_probe = subprocess.run(
            ["script", "-q", "-c", " ".join(cmd), "/dev/null"],
            check=False,
            input="",
            text=True,
            capture_output=True,
        )
        combined = "\n".join(
            [s for s in ((pty_probe.stdout or "").strip(), (pty_probe.stderr or "").strip()) if s]
        )
        if not combined:
            probe = subprocess.run(
                cmd,
                check=False,
                input="",
                text=True,
                capture_output=True,
            )
            combined = "\n".join(
                [s for s in ((probe.stdout or "").strip(), (probe.stderr or "").strip()) if s]
            )
        if combined:
            filtered_lines = []
            for line in combined.splitlines():
                lowered = line.strip().lower()
                if "enter the resulting authorization code here" in lowered:
                    continue
                if lowered == "aborted!" or lowered.endswith(": aborted!"):
                    continue
                filtered_lines.append(line)
            cleaned = "\n".join(filtered_lines).strip()
            if cleaned:
                print(cleaned)
            print("Awaiting authorization code. Re-run with --auth-code \"<CODE>\".")
        return False

    _run_cmd(cmd)
    return True


def _ensure_globus_cli_compat() -> None:
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            "from globus_cli.login_manager.scopes import CLI_SCOPE_REQUIREMENTS",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        return

    combined = f"{check.stdout}\n{check.stderr}"
    if "GCSCollectionScopes" not in combined:
        return

    print(
        "Detected globus-cli/globus-sdk mismatch on worker. "
        "Attempting in-place repair via pip with compute-compatible pins."
    )
    _run_cmd(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "globus-sdk>=3.59.0,<4",
            "globus-cli<4",
        ]
    )

    recheck = subprocess.run(
        [
            sys.executable,
            "-c",
            "from globus_cli.login_manager.scopes import CLI_SCOPE_REQUIREMENTS",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if recheck.returncode != 0:
        raise RuntimeError(
            "Globus CLI compatibility check failed after attempted repair.\n"
            f"stdout: {(recheck.stdout or '').strip()}\n"
            f"stderr: {(recheck.stderr or '').strip()}"
        )


def _print_whoami_best_effort() -> None:
    result = subprocess.run(
        ["globus", "whoami"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        output = (result.stdout or "").strip()
        print(output if output else "(no output)")
        return
    err = (result.stderr or "").strip()
    print(f"(failed rc={result.returncode}) {err or 'no stderr'}")


def _is_transfer_logged_in() -> bool:
    result = subprocess.run(
        ["globus", "whoami"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create/enqueue a ClearML task that performs Globus auth on an agent, "
            "or run worker auth mode when invoked by ClearML."
        )
    )
    parser.add_argument(
        "--type",
        dest="auth_type",
        choices=["transfer", "compute", "both"],
        default="transfer",
        help="Auth flow to run on the worker (default: transfer).",
    )
    parser.add_argument(
        "--queue",
        default="default",
        help="ClearML queue for the auth task (launch mode only).",
    )
    parser.add_argument(
        "--project-name",
        default="AmSC",
        help="ClearML project name.",
    )
    parser.add_argument(
        "--task-name",
        default="Globus auth (queued)",
        help="ClearML task name.",
    )
    parser.add_argument(
        "--auth-code",
        default=_env("CLEARML_GLOBUS_AUTH_CODE", ""),
        help=(
            "Authorization code for non-interactive 'globus login --no-local-server'. "
            "Useful when worker has no stdin."
        ),
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="After enqueue, stream task console output locally until task finishes.",
    )
    parser.add_argument(
        "--follow-interval",
        type=int,
        default=3,
        help="Polling interval in seconds for --follow (default: 3).",
    )
    parser.add_argument(
        "--follow-lines",
        type=int,
        default=200,
        help="How many recent log lines to fetch per poll for --follow (default: 200).",
    )
    parser.add_argument(
        "--one-shot",
        action="store_true",
        help=(
            "Local orchestrator mode: enqueue step-1 auth URL task, prompt for auth code, "
            "then enqueue step-2 completion task."
        ),
    )
    parser.add_argument(
        "--no-one-shot",
        dest="one_shot",
        action="store_false",
        help="Disable one-shot orchestration and run a single launch step.",
    )
    parser.set_defaults(one_shot=True)
    parser.add_argument(
        "--worker-mode",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_agent_context() -> bool:
    # ClearML agent typically sets one or more of these env vars.
    return any(
        os.getenv(name)
        for name in (
            "CLEARML_TASK_ID",
            "TRAINS_TASK_ID",
            "CLEARML_WORKER_ID",
            "TRAINS_WORKER_ID",
        )
    )


def _worker_main(args: argparse.Namespace) -> int:
    try:
        from clearml import Task

        Task.init(
            project_name=args.project_name,
            task_name=args.task_name,
            task_type=Task.TaskTypes.data_processing,
        )
    except Exception:
        pass
    _hydrate_auth_code_from_task(args)

    if args.auth_type in ("transfer", "both"):
        _ensure_globus_cli_compat()
        if not _is_transfer_logged_in():
            login_completed = _run_transfer_login(
                auth_code=str(args.auth_code or "").strip(),
            )
            if not login_completed:
                return 0
        _run_cmd(["globus", "whoami"])

    if args.auth_type in ("compute", "both"):
        _run_cmd(["globus-compute-endpoint", "login"])

    _print_whoami_best_effort()
    return 0


def _overlap_size(previous: list[str], current: list[str]) -> int:
    max_k = min(len(previous), len(current))
    for k in range(max_k, 0, -1):
        if previous[-k:] == current[:k]:
            return k
    return 0


def _follow_task_logs(task_id: str, interval_sec: int, num_lines: int) -> None:
    from clearml import Task

    print(f"Following task logs locally for task id={task_id} ...")
    previous_lines: list[str] = []
    terminal_states = {"completed", "failed", "stopped", "closed", "published"}

    while True:
        remote_task = Task.get_task(task_id=task_id)
        lines = list(remote_task.get_reported_console_output(number_of_reports=num_lines) or [])
        if lines:
            overlap = _overlap_size(previous_lines, lines)
            for line in lines[overlap:]:
                print(line)
            previous_lines = lines

        status = str(remote_task.get_status() or "").lower()
        if status in terminal_states:
            print(f"Auth task finished with status={status}")
            return
        time.sleep(max(1, interval_sec))


def _launch_main(args: argparse.Namespace) -> tuple[int, str]:
    from clearml import Task

    create_kwargs = {
        "project_name": args.project_name,
        "task_name": args.task_name,
        "task_type": Task.TaskTypes.data_processing,
        "script": __file__,
        "force_single_script_file": True,
        "argparse_args": [
            ("worker-mode", None),
            ("type", args.auth_type),
            ("project-name", args.project_name),
            ("task-name", args.task_name),
            *((("auth-code", args.auth_code),) if args.auth_code else ()),
        ],
    }
    try:
        task = Task.create(reuse_last_task_id=False, **create_kwargs)
    except TypeError as exc:
        if "reuse_last_task_id" not in str(exc):
            raise
        # Older ClearML clients may reuse prior tasks by name.
        # Add a timestamp suffix to force a fresh task carrying current args.
        create_kwargs["task_name"] = f"{args.task_name} [{int(time.time())}]"
        task = Task.create(**create_kwargs)

    # Force worker mode when this task is executed on an agent.
    task.set_parameters_as_dict(
        {
            "env:CLEARML_GLOBUS_AUTH_WORKER_MODE": "1",
            "env:CLEARML_GLOBUS_AUTH_CODE": str(args.auth_code or ""),
        }
    )
    Task.enqueue(task, queue_name=args.queue)
    print(f"Enqueued auth task id={task.id} queue={args.queue}")
    try:
        url = task.get_output_log_web_page()
    except Exception:
        url = ""
    if url:
        print(f"ClearML results page: {url}")
    print("Watch task logs for the Globus URL/device code to complete login.")
    if args.follow:
        _follow_task_logs(
            task_id=task.id,
            interval_sec=args.follow_interval,
            num_lines=args.follow_lines,
        )
    return 0, task.id


def _one_shot_main(args: argparse.Namespace) -> int:
    from clearml import Task

    if args.auth_type not in ("transfer", "both"):
        print("--one-shot currently supports --type transfer|both.")
        return 2
    if str(args.auth_code or "").strip():
        print("--one-shot should be used without --auth-code. It will prompt you.")
        return 2

    step1 = argparse.Namespace(**vars(args))
    step1.one_shot = False
    step1.follow = True
    step1.auth_code = ""
    step1.task_name = f"{args.task_name} [step1]"
    rc, step1_task_id = _launch_main(step1)
    if rc != 0:
        return rc

    # If step-1 logs do not show auth URL prompt, auth is likely already valid.
    try:
        step1_task = Task.get_task(task_id=step1_task_id)
    except Exception:
        step1_task = None

    if step1_task is not None:
        try:
            logs = "\n".join(
                step1_task.get_reported_console_output(number_of_reports=max(200, args.follow_lines))
            )
        except Exception:
            logs = ""
        if "Please authenticate with Globus here:" not in logs:
            return 0

    code = input("Paste Globus Authorization Code: ").strip()
    if not code:
        print("No auth code provided.")
        return 1

    step2 = argparse.Namespace(**vars(args))
    step2.one_shot = False
    step2.follow = True
    step2.auth_code = code
    step2.task_name = f"{args.task_name} [step2]"
    step2_rc, _ = _launch_main(step2)
    return step2_rc


def main() -> int:
    args = _parse_args()
    if args.worker_mode or _env_bool("CLEARML_GLOBUS_AUTH_WORKER_MODE") or _is_agent_context():
        return _worker_main(args)
    if args.one_shot:
        return _one_shot_main(args)
    rc, _ = _launch_main(args)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
