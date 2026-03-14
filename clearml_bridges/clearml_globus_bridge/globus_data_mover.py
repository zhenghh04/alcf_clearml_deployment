from pathlib import Path
from typing import Any, Dict, Optional

from clearml import Task


class GlobusDataMover:
    """Create ClearML tasks that run Globus Transfer data movement."""

    def create(
        self,
        project_name: str,
        task_name: str,
        src_endpoint: str,
        dst_endpoint: str,
        src_path: str,
        dst_path: str,
        task_type: Task.TaskTypes = Task.TaskTypes.data_processing,
        label: str = "clearml-data-movement",
        recursive: bool = False,
        sync_level: Optional[str] = None,
        poll_interval: int = 10,
        dry_run: bool = False,
        no_wait: bool = False,
        token: Optional[str] = None,
        token_env_var: str = "GLOBUS_TRANSFER_ACCESS_TOKEN",
        launcher_binary: str = "python",
        user_properties: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        if not all([src_endpoint, dst_endpoint, src_path, dst_path]):
            raise ValueError(
                "Data movement requires src_endpoint, dst_endpoint, src_path, and dst_path."
            )

        argparse_args = [
            ("project-name", project_name),
            ("task-name", task_name),
            ("src-endpoint", src_endpoint),
            ("dst-endpoint", dst_endpoint),
            ("src-path", src_path),
            ("dst-path", dst_path),
            ("label", label),
            ("poll-interval", str(poll_interval)),
        ]
        if token:
            argparse_args.append(("token", token))
        else:
            argparse_args.append(("token-env-var", token_env_var))
        if recursive:
            argparse_args.append(("recursive", None))
        if sync_level:
            argparse_args.append(("sync-level", sync_level))
        if dry_run:
            argparse_args.append(("dry-run", None))
        if no_wait:
            argparse_args.append(("no-wait", None))

        create_kwargs: Dict[str, Any] = {
            "project_name": project_name,
            "task_name": task_name,
            "task_type": task_type,
            "binary": launcher_binary,
            "reuse_last_task_id": False,
            "argparse_args": argparse_args,
            "script": str(Path(__file__).with_name("data_movement.py")),
            "force_single_script_file": True,
        }

        try:
            task = Task.create(**create_kwargs)
        except TypeError as exc:
            if "reuse_last_task_id" not in str(exc):
                raise
            create_kwargs.pop("reuse_last_task_id", None)
            task = Task.create(**create_kwargs)

        task.set_parameters_as_dict(
            {
                "Args/src-endpoint": src_endpoint,
                "Args/dst-endpoint": dst_endpoint,
                "Args/src-path": src_path,
                "Args/dst-path": dst_path,
                "env:GLOBUS_SRC_ENDPOINT": src_endpoint,
                "env:GLOBUS_DST_ENDPOINT": dst_endpoint,
                "env:GLOBUS_SRC_PATH": src_path,
                "env:GLOBUS_DST_PATH": dst_path,
                "env:GLOBUS_LABEL": label,
                "env:GLOBUS_RECURSIVE": "1" if recursive else "0",
                "env:GLOBUS_SYNC_LEVEL": sync_level or "",
                "env:GLOBUS_POLL_INTERVAL": str(poll_interval),
                "env:GLOBUS_DRY_RUN": "1" if dry_run else "0",
                "env:GLOBUS_NO_WAIT": "1" if no_wait else "0",
                "env:GLOBUS_TRANSFER_ACCESS_TOKEN_ENV": token_env_var,
            }
        )
        if token:
            task.set_parameters_as_dict({"env:GLOBUS_TRANSFER_ACCESS_TOKEN": token})

        if user_properties:
            filtered_user_properties = {k: v for k, v in user_properties.items() if v is not None}
            if filtered_user_properties:
                task.set_user_properties(**filtered_user_properties)

        if tags:
            task.set_tags(tags)

        return task
