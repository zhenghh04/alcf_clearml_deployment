import json
import os
from typing import Any, Dict, Optional, Sequence

from clearml import Task


class GlobusComputeLauncher:
    """Create ClearML tasks that submit work to Globus Compute endpoints."""

    def create(
        self,
        project_name: str,
        task_name: str,
        repo: str,
        branch: str,
        working_directory: str,
        task_type: Task.TaskTypes = Task.TaskTypes.data_processing,
        endpoint_id: Optional[str] = None,
        script: Optional[str] = None,
        binary: str = "/bin/bash",
        launcher_module: str = "clearml_globus_bridge.submit_globus_job",
        launcher_script: Optional[str] = None,
        launcher_binary: str = "python",
        launcher_working_directory: Optional[str] = None,
        script_working_directory: Optional[str] = None,
        clone_repo_for_script: bool = True,
        input_value: int = 7,
        poll_interval: int = 5,
        timeout_sec: int = 900,
        artifact_path: str = "globus_result.json",
        script_args: Optional[Sequence[str]] = None,
        endpoint_config: Optional[Dict[str, Any]] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        selected_endpoint = endpoint_id or os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID")
        if not selected_endpoint:
            raise ValueError(
                "endpoint_id is required. Pass endpoint_id or export GLOBUS_COMPUTE_ENDPOINT_ID."
            )
        argparse_args = [
            ("endpoint-id", selected_endpoint),
            ("input-value", str(input_value)),
            ("poll-interval", str(poll_interval)),
            ("timeout-sec", str(timeout_sec)),
            ("artifact-path", artifact_path),
        ]

        if endpoint_config:
            argparse_args.append(("endpoint-config-json", json.dumps(endpoint_config)))
        if script:
            argparse_args.append(("script", script))
            argparse_args.append(("binary", binary))
            if script_working_directory:
                argparse_args.append(("working-directory", script_working_directory))
            if script_args:
                argparse_args.append(("script-args-json", json.dumps(list(script_args))))
            if clone_repo_for_script and not os.path.isabs(script):
                argparse_args.append(("clone-repo", "true"))
                argparse_args.append(("repo-url", repo))
                argparse_args.append(("repo-branch", branch))
                argparse_args.append(("repo-working-directory", working_directory))

        create_kwargs: Dict[str, Any] = {
            "project_name": project_name,
            "task_name": task_name,
            "task_type": task_type,
            "repo": repo,
            "branch": branch,
            "working_directory": launcher_working_directory or working_directory,
            "binary": launcher_binary,
            "argparse_args": argparse_args,
        }
        if launcher_script:
            create_kwargs["script"] = launcher_script
        else:
            create_kwargs["module"] = launcher_module
            # Ensure clearml_globus_bridge package is importable on the agent.
            # Requires working directory at repository root.
            create_kwargs["packages"] = ["-e ."]

        task = Task.create(**create_kwargs)

        task.set_parameters_as_dict(
            {
                "Args/endpoint-id": selected_endpoint,
                "env:GLOBUS_COMPUTE_ENDPOINT_ID": selected_endpoint,
            }
        )

        clearml_user_properties = dict(user_properties or {})
        clearml_user_properties = {
            key: value for key, value in clearml_user_properties.items() if value is not None
        }
        if clearml_user_properties:
            task.set_user_properties(**clearml_user_properties)

        if tags:
            task.set_tags(tags)

        return task
