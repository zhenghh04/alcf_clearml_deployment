import json
import os
from typing import Any, Dict, Optional

from clearml import Task


class IRILauncher:
    """Create ClearML tasks that submit work to an IRI-compatible facility API."""

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
        api_base_url: Optional[str] = None,
        submit_path: Optional[str] = None,
        status_path_template: Optional[str] = None,
        result_path_template: str = "",
        method: str = "POST",
        job_payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        id_field: str = "id",
        status_field: str = "status",
        result_field: str = "",
        terminal_states: Optional[list[str]] = None,
        success_states: Optional[list[str]] = None,
        poll_interval: int = 10,
        timeout_sec: int = 1800,
        request_timeout_sec: int = 60,
        artifact_path: str = "iri_result.json",
        auth_header_name: str = "Authorization",
        auth_token_prefix: str = "Bearer ",
        launcher_module: str = "clearml_iri_bridge.submit_iri_job",
        launcher_script: Optional[str] = None,
        launcher_binary: str = "python",
        launcher_working_directory: Optional[str] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        selected_api_base_url = api_base_url or os.getenv("IRI_API_BASE_URL")
        selected_submit_path = submit_path or os.getenv("IRI_SUBMIT_PATH", "/jobs")
        selected_status_path_template = status_path_template or os.getenv(
            "IRI_STATUS_PATH_TEMPLATE", "/jobs/{job_id}"
        )
        if not selected_api_base_url:
            raise ValueError("IRI API base URL is required. Pass api_base_url or export IRI_API_BASE_URL.")

        argparse_args = [
            ("project-name", project_name),
            ("task-name", task_name),
            ("task-type", self._task_type_to_cli_value(task_type)),
            ("api-base-url", selected_api_base_url),
            ("submit-path", selected_submit_path),
            ("status-path-template", selected_status_path_template),
            ("method", method),
            ("id-field", id_field),
            ("status-field", status_field),
            ("poll-interval", str(poll_interval)),
            ("timeout-sec", str(timeout_sec)),
            ("request-timeout-sec", str(request_timeout_sec)),
            ("artifact-path", artifact_path),
            ("auth-header-name", auth_header_name),
            ("auth-token-prefix", auth_token_prefix),
        ]
        if result_field:
            argparse_args.append(("result-field", result_field))
        if result_path_template:
            argparse_args.append(("result-path-template", result_path_template))
        if job_payload:
            argparse_args.append(("job-payload-json", json.dumps(job_payload)))
        if headers:
            argparse_args.append(("headers-json", json.dumps(headers)))
        if terminal_states:
            argparse_args.append(("terminal-states-json", json.dumps(terminal_states)))
        if success_states:
            argparse_args.append(("success-states-json", json.dumps(success_states)))

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
            create_kwargs["packages"] = ["-e ."]

        task = Task.create(**create_kwargs)

        params_to_set: Dict[str, str] = {
            "Args/api-base-url": selected_api_base_url,
            "Args/submit-path": selected_submit_path,
            "Args/status-path-template": selected_status_path_template,
            "env:IRI_API_BASE_URL": selected_api_base_url,
            "env:IRI_SUBMIT_PATH": selected_submit_path,
            "env:IRI_STATUS_PATH_TEMPLATE": selected_status_path_template,
        }
        if result_path_template:
            params_to_set["Args/result-path-template"] = result_path_template
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
