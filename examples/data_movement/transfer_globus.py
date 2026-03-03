from __future__ import print_function

import argparse
import os
import sys
from pathlib import Path

from clearml import Task

# Prefer local checkout import when running from repository.
REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGES_ROOT = REPO_ROOT / "clearml_bridges"
if str(BRIDGES_ROOT) not in sys.path:
    sys.path.insert(0, str(BRIDGES_ROOT))

from clearml_globus_bridge import GlobusDataMover


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


def main():
    parser = argparse.ArgumentParser(
        description="Create a ClearML Globus data movement task using GlobusDataMover."
    )
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
    parser.add_argument("--project-name", default=_env("CLEARML_PROJECT_NAME", "AmSC"))
    parser.add_argument("--task-name", default=_env("CLEARML_TASK_NAME", "Globus data movement"))
    parser.add_argument("--queue", default=_env("QUEUE"))
    parser.add_argument(
        "--token",
        default=_env("GLOBUS_TRANSFER_ACCESS_TOKEN", _env("GLOBUS_ACCESS_TOKEN")),
        help="Globus Transfer access token passed to GlobusDataMover task.",
    )
    args = parser.parse_args()

    if not all([args.src_endpoint, args.dst_endpoint, args.src_path, args.dst_path]):
        raise ValueError(
            "Missing required args: --src-endpoint, --dst-endpoint, --src-path, --dst-path"
        )

    mover = GlobusDataMover()
    task = mover.create(
        project_name=args.project_name,
        task_name=args.task_name,
        src_endpoint=args.src_endpoint,
        dst_endpoint=args.dst_endpoint,
        src_path=args.src_path,
        dst_path=args.dst_path,
        label=args.label,
        recursive=args.recursive,
        sync_level=args.sync_level,
        poll_interval=args.poll_interval,
        dry_run=args.dry_run,
        no_wait=args.no_wait,
        token=args.token,
    )

    if args.queue:
        Task.enqueue(task, queue_name=args.queue)
        print(f"Enqueued transfer task id={task.id} queue={args.queue}")
    else:
        print(f"Created transfer task id={task.id} (not enqueued)")


if __name__ == "__main__":
    main()
