import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from clearml import Task


class GlobusComputeLauncher:
    """Create ClearML tasks that submit work to Globus Compute endpoints."""

    DEFAULT_PACKAGES = [
        "clearml>=2.1.3",
        "globus-sdk==3.65.0",
        "globus-compute-sdk==4.6.0",
    ]

    @staticmethod
    def _task_type_to_cli_value(task_type: Any) -> str:
        value = getattr(task_type, "value", None)
        if value:
            return str(value)
        return str(task_type)

    def create(
        self,
        project_name: str,
        task_name: str,
        repo: str,
        branch: str,
        working_directory: str,
        task_type: Task.TaskTypes = Task.TaskTypes.data_processing,
        endpoint_id: Optional[str] = None,
        endpoint_name: Optional[str] = None,
        script: Optional[str] = None,
        binary: str = "/bin/bash",
        launcher_module: str = "clearml_globus_bridge.submit_globus_job",
        launcher_script: Optional[str] = str(Path(__file__).with_name("submit_globus_job.py")),
        launcher_binary: str = "python",
        launcher_working_directory: Optional[str] = None,
        script_working_directory: Optional[str] = None,
        clone_repo: bool = True,
        clone_repo_for_script: Optional[bool] = None,
        input_value: int = 7,
        poll_interval: int = 5,
        timeout_sec: int = 900,
        artifact_path: str = "globus_result.json",
        script_args: Optional[Sequence[str]] = None,
        endpoint_config: Optional[Dict[str, Any]] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        packages: Optional[Sequence[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        effective_clone_repo = (
            clone_repo if clone_repo_for_script is None else clone_repo_for_script
        )
        selected_endpoint_id = (endpoint_id or "").strip() or None
        selected_endpoint_name = (endpoint_name or "").strip() or None
        if not selected_endpoint_id and not selected_endpoint_name:
            raise ValueError(
                "Endpoint is required. Pass endpoint_id or endpoint_name."
            )
        argparse_args = [
            ("project_name", project_name),
            ("task_name", task_name),
            ("task_type", self._task_type_to_cli_value(task_type)),
            ("input_value", str(input_value)),
            ("poll_interval", str(poll_interval)),
            ("timeout_sec", str(timeout_sec)),
            ("artifact_path", artifact_path),
        ]
        if selected_endpoint_id:
            argparse_args.append(("endpoint_id", selected_endpoint_id))
        if selected_endpoint_name:
            argparse_args.append(("endpoint_name", selected_endpoint_name))
        if token:
            argparse_args.append(("token", token))
        if endpoint_config:
            argparse_args.append(("endpoint_config_json", json.dumps(endpoint_config)))
        if script:
            argparse_args.append(("script", script))
            argparse_args.append(("binary", binary))
            if script_working_directory:
                argparse_args.append(("working_directory", script_working_directory))
            if script_args:
                argparse_args.append(("script_args_json", json.dumps(list(script_args))))
            if effective_clone_repo and not os.path.isabs(script):
                argparse_args.append(("clone_repo", "true"))
                argparse_args.append(("repo_url", repo))
                argparse_args.append(("repo_branch", branch))
                argparse_args.append(("repo_working_directory", working_directory))

        create_kwargs: Dict[str, Any] = {
            "project_name": project_name,
            "task_name": task_name,
            "task_type": task_type,
            "repo": repo,
            "branch": branch,
            "working_directory": launcher_working_directory or working_directory,
            "binary": launcher_binary,
            "argparse_args": argparse_args,
            "packages": list(packages or self.DEFAULT_PACKAGES),
        }
        if launcher_script:
            create_kwargs["script"] = launcher_script
            create_kwargs["force_single_script_file"] = True
        else:
            create_kwargs["module"] = launcher_module

        task = Task.create(**create_kwargs)
        for param_name in ("bridge/token", "Args/token", "General/token", "token"):
            try:
                task.delete_parameter(param_name, force=True)
            except Exception:
                pass
        params_to_set: Dict[str, str] = {}
        params_to_set["env:GLOBUS_DEBUG_ENV"] = "1"
        if selected_endpoint_id:
            params_to_set["Args/endpoint_id"] = selected_endpoint_id
            params_to_set["env:GLOBUS_COMPUTE_ENDPOINT_ID"] = selected_endpoint_id
        if selected_endpoint_name:
            params_to_set["Args/endpoint_name"] = selected_endpoint_name
            params_to_set["env:GLOBUS_COMPUTE_ENDPOINT_NAME"] = selected_endpoint_name
        if params_to_set:
            task.set_parameters_as_dict(params_to_set)

        clearml_user_properties = dict(user_properties or {})
        clearml_user_properties = {
            key: value for key, value in clearml_user_properties.items() if value is not None
        }
        if clearml_user_properties:
            task.set_user_properties(**clearml_user_properties)

        if tags:
            task.set_tags(tags)

        return task


def _parse_task_type(value: str) -> Task.TaskTypes:
    normalized = value.strip()
    if not normalized:
        raise ValueError("task_type cannot be empty")
    for task_type in Task.TaskTypes:
        if task_type.value == normalized:
            return task_type
    raise ValueError(
        f"Unsupported task type '{value}'. Use one of: "
        + ", ".join(sorted(task_type.value for task_type in Task.TaskTypes))
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and optionally enqueue a ClearML task that submits work to Globus Compute."
    )
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--working-directory", default=".")
    parser.add_argument("--task-type", default=Task.TaskTypes.data_processing.value)
    parser.add_argument("--endpoint-id", default="")
    parser.add_argument("--endpoint-name", default="")
    parser.add_argument("--script", default="")
    parser.add_argument("--binary", default="/bin/bash")
    parser.add_argument("--launcher-binary", default="python")
    parser.add_argument("--launcher-working-directory", default="")
    parser.add_argument("--script-working-directory", default="")
    parser.add_argument("--clone-repo", dest="clone_repo", action="store_true")
    parser.add_argument("--no-clone-repo", dest="clone_repo", action="store_false")
    parser.set_defaults(clone_repo=True)
    parser.add_argument("--input-value", type=int, default=7)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--artifact-path", default="globus_result.json")
    parser.add_argument("--script-args-json", default="")
    parser.add_argument("--endpoint-config-json", default="")
    parser.add_argument("--packages-json", default="")
    parser.add_argument("--tags-json", default="")
    parser.add_argument("--queue", default="")
    parser.add_argument("--token", default="")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    script_args = json.loads(args.script_args_json) if args.script_args_json else None
    endpoint_config = (
        json.loads(args.endpoint_config_json) if args.endpoint_config_json else None
    )
    packages = json.loads(args.packages_json) if args.packages_json else None
    tags = json.loads(args.tags_json) if args.tags_json else None

    launcher = GlobusComputeLauncher()
    task = launcher.create(
        project_name=args.project_name,
        task_name=args.task_name,
        repo=args.repo,
        branch=args.branch,
        working_directory=args.working_directory,
        task_type=_parse_task_type(args.task_type),
        endpoint_id=args.endpoint_id or None,
        endpoint_name=args.endpoint_name or None,
        script=args.script or None,
        binary=args.binary,
        launcher_binary=args.launcher_binary,
        launcher_working_directory=args.launcher_working_directory or None,
        script_working_directory=args.script_working_directory or None,
        clone_repo=args.clone_repo,
        input_value=args.input_value,
        poll_interval=args.poll_interval,
        timeout_sec=args.timeout_sec,
        artifact_path=args.artifact_path,
        script_args=script_args,
        endpoint_config=endpoint_config,
        token=args.token or None,
        packages=packages,
        tags=tags,
    )
    if args.queue:
        Task.enqueue(task, queue_name=args.queue)
        print(f"Enqueued task: {task.id} on queue {args.queue}")
    else:
        print(f"Created task: {task.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
