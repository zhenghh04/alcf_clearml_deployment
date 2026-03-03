from __future__ import print_function

import argparse
import os
from clearml import Task


def _env(name, default=None):
    value = os.environ.get(name)
    return value if value is not None else default


def main():
    parser = argparse.ArgumentParser(description="Enqueue Globus data movement task")
    parser.add_argument("--src-endpoint", default=_env("GLOBUS_SRC_ENDPOINT"))
    parser.add_argument("--dst-endpoint", default=_env("GLOBUS_DST_ENDPOINT"))
    parser.add_argument("--src-path", default=_env("GLOBUS_SRC_PATH"))
    parser.add_argument("--dst-path", default=_env("GLOBUS_DST_PATH"))
    parser.add_argument("--label", default=_env("GLOBUS_LABEL", "clearml-data-movement"))
    parser.add_argument("--recursive", action="store_true", default=False)
    parser.add_argument("--sync-level", default=_env("GLOBUS_SYNC_LEVEL"))
    parser.add_argument("--poll-interval", default=_env("GLOBUS_POLL_INTERVAL", "10"))
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--no-wait", action="store_true", default=False)
    parser.add_argument("--queue", default=_env("QUEUE", "default"))
    args = parser.parse_args()

    if not all([args.src_endpoint, args.dst_endpoint, args.src_path, args.dst_path]):
        raise ValueError(
            "Missing required args: --src-endpoint, --dst-endpoint, --src-path, --dst-path"
        )

    script_path = os.path.join(os.path.dirname(__file__), "transfer_globus.py")
    created_task = Task.create(
        project_name="AmSC",
        task_name="Globus data movement (enqueued)",
        script=script_path,
        force_single_script_file=True,
    )
    created_task.set_parameters_as_dict(
        {
            "env:GLOBUS_SRC_ENDPOINT": args.src_endpoint,
            "env:GLOBUS_DST_ENDPOINT": args.dst_endpoint,
            "env:GLOBUS_SRC_PATH": args.src_path,
            "env:GLOBUS_DST_PATH": args.dst_path,
            "env:GLOBUS_LABEL": args.label,
            "env:GLOBUS_RECURSIVE": "1" if args.recursive else "0",
            "env:GLOBUS_SYNC_LEVEL": args.sync_level or "",
            "env:GLOBUS_POLL_INTERVAL": str(args.poll_interval),
            "env:GLOBUS_DRY_RUN": "1" if args.dry_run else "0",
            "env:GLOBUS_NO_WAIT": "1" if args.no_wait else "0",
        }
    )
    Task.enqueue(created_task, queue_name=args.queue)


if __name__ == "__main__":
    main()
