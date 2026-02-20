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
        launcher_script: str = "./tasks/submit_globus_job.py",
        launcher_binary: str = "python",
        launcher_working_directory: Optional[str] = None,
        script_working_directory: Optional[str] = None,
        clone_repo_for_script: bool = True,
        input_value: int = 7,
        poll_interval: int = 5,
        timeout_sec: int = 900,
        artifact_path: str = "globus_result.json",
        script_args: Optional[Sequence[str]] = None,
        account: Optional[str] = None,
        queue: Optional[str] = None,
        scheduler_queue: Optional[str] = None,
        partition: Optional[str] = None,
        num_nodes: Optional[int] = None,
        cores_per_node: Optional[int] = None,
        walltime: Optional[str] = None,
        endpoint_config: Optional[Dict[str, Any]] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        selected_endpoint = endpoint_id or os.getenv("GLOBUS_COMPUTE_ENDPOINT_ID")
        if not selected_endpoint:
            raise ValueError(
                "endpoint_id is required. Pass endpoint_id or export GLOBUS_COMPUTE_ENDPOINT_ID."
            )
        selected_queue = queue or scheduler_queue

        argparse_args = [
            ("endpoint-id", selected_endpoint),
            ("input-value", str(input_value)),
            ("poll-interval", str(poll_interval)),
            ("timeout-sec", str(timeout_sec)),
            ("artifact-path", artifact_path),
        ]

        if account:
            argparse_args.append(("account", account))
        if selected_queue:
            argparse_args.append(("scheduler-queue", selected_queue))
        if partition:
            argparse_args.append(("partition", partition))
        if num_nodes is not None:
            argparse_args.append(("num-nodes", str(num_nodes)))
        if cores_per_node is not None:
            argparse_args.append(("cores-per-node", str(cores_per_node)))
        if walltime:
            argparse_args.append(("walltime", walltime))
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

        task = Task.create(
            project_name=project_name,
            task_name=task_name,
            task_type=task_type,
            repo=repo,
            branch=branch,
            working_directory=launcher_working_directory or working_directory,
            script=launcher_script,
            binary=launcher_binary,
            argparse_args=argparse_args,
        )

        task.set_parameters_as_dict(
            {
                "Args/endpoint-id": selected_endpoint,
                "env:GLOBUS_COMPUTE_ENDPOINT_ID": selected_endpoint,
            }
        )

        clearml_user_properties = {
            "account": account,
            "queue": selected_queue,
            "partition": partition,
            "num_nodes": num_nodes,
            "cores_per_node": cores_per_node,
            "walltime": walltime,
        }
        if user_properties:
            clearml_user_properties.update(user_properties)
        clearml_user_properties = {
            key: value for key, value in clearml_user_properties.items() if value is not None
        }
        if clearml_user_properties:
            task.set_user_properties(**clearml_user_properties)

        if tags:
            task.set_tags(tags)

        return task
