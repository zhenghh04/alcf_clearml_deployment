import json
import os
import shlex
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from clearml import Task


FACILITY_BASE_URLS = {
    "alcf": "https://api.alcf.anl.gov",
    "nersc": "https://api.nersc.gov",
    "olcf": "https://s3m.olcf.ornl.gov",
}


def _looks_like_uuid(value: str) -> bool:
    text = value.strip().lower()
    parts = text.split("-")
    if len(parts) != 5:
        return False
    expected_lengths = [8, 4, 4, 4, 12]
    return all(len(part) == expected for part, expected in zip(parts, expected_lengths))


def _build_auth_headers(auth_header_name: str, auth_token_prefix: str) -> Dict[str, str]:
    token = (os.getenv("IRI_API_TOKEN") or "").strip()
    if not token:
        return {}
    return {auth_header_name: f"{auth_token_prefix}{token}"}


def _resolve_alcf_resource_id(
    *,
    api_base_url: str,
    system: str,
    auth_header_name: str,
    auth_token_prefix: str,
    request_timeout_sec: int,
) -> str:
    normalized_system = system.strip()
    if not normalized_system or _looks_like_uuid(normalized_system):
        return normalized_system

    headers = _build_auth_headers(auth_header_name, auth_token_prefix)
    if not headers:
        return ""

    resources_url = f"{api_base_url.rstrip('/')}/api/v1/status/resources?resource_type=compute"
    try:
        response = requests.get(resources_url, headers=headers, timeout=request_timeout_sec)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return ""

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("resources")
    else:
        items = None
    if not isinstance(items, list):
        return ""

    target = normalized_system.lower()
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("id") or "").strip()
        if not candidate_id:
            continue
        names = {
            str(item.get("name") or "").strip().lower(),
            str(item.get("system") or "").strip().lower(),
            str(item.get("resource_name") or "").strip().lower(),
        }
        if target in names:
            return candidate_id
    return ""


def _escape_graphql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_script_text(script_text: str) -> str:
    lines = []
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#!"):
            continue
        lines.append(line)
    return "; ".join(lines)


def _normalize_precommands(
    precommand: str = "",
    precommands: Optional[list[str]] = None,
) -> str:
    commands = []
    normalized_precommand = precommand.strip()
    if normalized_precommand:
        commands.append(normalized_precommand)
    if precommands:
        for item in precommands:
            normalized = str(item).strip()
            if normalized:
                commands.append(normalized)
    normalized = []
    for command in commands:
        text = _normalize_script_text(command)
        if text:
            normalized.append(text)
    return "; ".join(normalized)


def _combine_shell_text(prelude: str, main: str) -> str:
    parts = [part for part in (prelude, main) if part]
    return "; ".join(parts)


def build_job_payload(
    *,
    scheduler: str,
    name: str,
    directory: str,
    stdout_path: str,
    stderr_path: str,
    executable: str = "/bin/bash",
    arguments: Optional[list[str]] = None,
    command: str = "",
    script: str = "",
    script_path: str = "",
    script_remote_path: str = "",
    precommand: str = "",
    precommands: Optional[list[str]] = None,
    account: str = "",
    queue_name: str = "",
    duration: Optional[int] = None,
    node_count: Optional[int] = None,
    note_count: Optional[int] = None,
    custom_attributes: Optional[Dict[str, Any]] = None,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    scheduler_name = scheduler.strip().lower()
    if scheduler_name not in {"pbs", "slurm"}:
        raise ValueError("scheduler must be one of: pbs, slurm")

    if arguments and (command or script or script_path or script_remote_path):
        raise ValueError("Pass either arguments or command/script/script_path/script_remote_path, not both.")

    resolved_arguments = list(arguments or [])
    prelude = _normalize_precommands(precommand, precommands)
    if sum(bool(value) for value in (script, script_path, script_remote_path)) > 1:
        raise ValueError("Pass only one of script, script_path, or script_remote_path.")
    remote_script_path = script_path or script_remote_path
    if remote_script_path:
        remote_command = f"/bin/bash -l {shlex.quote(remote_script_path)}"
        resolved_arguments = ["-lc", _combine_shell_text(prelude, remote_command)]
    elif script:
        resolved_arguments = ["-lc", _escape_graphql_string(_combine_shell_text(prelude, _normalize_script_text(script)))]
    elif command:
        resolved_arguments = ["-lc", _escape_graphql_string(_combine_shell_text(prelude, _normalize_script_text(command)))]

    if not resolved_arguments:
        raise ValueError(
            "Job payload requires either arguments, command, script, script_path, or script_remote_path."
        )

    attrs: Dict[str, Any] = dict(extra_attributes or {})
    if account:
        attrs["account"] = account
    if queue_name:
        attrs["queue_name"] = queue_name
    if duration is not None:
        attrs["duration"] = duration
    if custom_attributes:
        attrs["custom_attributes"] = dict(custom_attributes)
    if scheduler_name == "slurm":
        # Preserve the scheduler choice for bridges that need to branch later.
        attrs.setdefault("scheduler", "slurm")

    payload = {
        "name": name,
        "executable": executable,
        "arguments": resolved_arguments,
        "directory": directory,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "attributes": attrs,
    }
    resolved_node_count = node_count if node_count is not None else note_count
    if resolved_node_count is not None:
        payload["resources"] = {"node_count": int(resolved_node_count)}
    return payload


def build_alcf_job_payload(
    *,
    name: str,
    directory: str,
    stdout_path: str,
    stderr_path: str,
    account: str,
    queue_name: str,
    duration: int,
    node_count: Optional[int] = None,
    note_count: Optional[int] = None,
    executable: str = "/bin/bash",
    arguments: Optional[list[str]] = None,
    command: str = "",
    script: str = "",
    script_path: str = "",
    script_remote_path: str = "",
    precommand: str = "",
    precommands: Optional[list[str]] = None,
    custom_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return build_job_payload(
        scheduler="pbs",
        name=name,
        directory=directory,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        account=account,
        queue_name=queue_name,
        duration=duration,
        node_count=node_count,
        note_count=note_count,
        executable=executable,
        arguments=arguments,
        command=command,
        script=script,
        script_path=script_path,
        script_remote_path=script_remote_path,
        precommand=precommand,
        precommands=precommands,
        custom_attributes=custom_attributes,
    )


class IRILauncher:
    """Create ClearML tasks that submit work to an IRI-compatible facility API."""

    DEFAULT_PACKAGES = [
        "clearml>=2.1.3",
        "requests>=2.31.0",
    ]

    @staticmethod
    def _task_type_to_cli_value(task_type: Any) -> str:
        value = getattr(task_type, "value", None)
        if value:
            return str(value)
        return str(task_type)

    @staticmethod
    def _resolve_facility(facility: Optional[str], api_base_url: Optional[str]) -> tuple[str, str]:
        selected_facility = (facility or os.getenv("IRI_FACILITY", "")).strip().lower()
        if selected_facility:
            if selected_facility not in FACILITY_BASE_URLS:
                supported = ", ".join(sorted(FACILITY_BASE_URLS))
                raise ValueError(
                    f"Unsupported facility '{selected_facility}'. Use one of: {supported}."
                )
            return selected_facility, FACILITY_BASE_URLS[selected_facility]

        selected_api_base_url = (api_base_url or os.getenv("IRI_API_BASE_URL", "")).strip()
        if not selected_api_base_url:
            raise ValueError(
                "IRI facility is required. Pass facility='alcf'|'nersc'|'olcf' "
                "or export IRI_FACILITY."
            )
        print("Selecting custom IRI API base URL:", selected_api_base_url)
        return "custom", selected_api_base_url

    def create(
        self,
        project_name: str,
        task_name: str,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        working_directory: str = ".",
        task_type: Task.TaskTypes = Task.TaskTypes.data_processing,
        facility: Optional[str] = None,
        api_base_url: Optional[str] = None,
        system: Optional[str] = None,
        submit_path: Optional[str] = None,
        status_path_template: Optional[str] = None,
        cancel_path_template: Optional[str] = None,
        result_path_template: str = "",
        method: str = "POST",
        job_payload: Optional[Dict[str, Any]] = None,
        job_payload_file: Optional[str] = None,
        script: str = "",
        script_file: Optional[str] = None,
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
        clone_repo_on_job: bool = True,
        user_properties: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        selected_facility, selected_api_base_url = self._resolve_facility(facility, api_base_url)
        selected_system = system or os.getenv("IRI_SYSTEM") or os.getenv("IRI_RESOURCE_ID")
        selected_submit_path = submit_path or os.getenv(
            "IRI_SUBMIT_PATH", "/api/v1/compute/job/{system}"
        )
        selected_status_path_template = status_path_template or os.getenv(
            "IRI_STATUS_PATH_TEMPLATE", "/api/v1/compute/status/{system}/{job_id}"
        )
        selected_cancel_path_template = cancel_path_template or os.getenv(
            "IRI_CANCEL_PATH_TEMPLATE", "/api/v1/compute/cancel/{system}/{job_id}"
        )
        if not selected_system:
            raise ValueError("IRI system is required. Pass system or export IRI_SYSTEM.")

        resolved_resource_id = ""
        if selected_facility == "alcf":
            resolved_resource_id = _resolve_alcf_resource_id(
                api_base_url=selected_api_base_url,
                system=selected_system,
                auth_header_name=auth_header_name,
                auth_token_prefix=auth_token_prefix,
                request_timeout_sec=request_timeout_sec,
            )

        argparse_args = [
            ("project-name", project_name),
            ("task-name", task_name),
            ("task-type", self._task_type_to_cli_value(task_type)),
            ("facility", selected_facility),
            ("system", selected_system),
            ("submit-path", selected_submit_path),
            ("status-path-template", selected_status_path_template),
            ("cancel-path-template", selected_cancel_path_template),
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
        if job_payload and job_payload_file:
            raise ValueError("Pass only one of job_payload or job_payload_file.")
        if script and script_file:
            raise ValueError("Pass only one of script or script_file.")
        if job_payload_file:
            job_payload = json.loads(Path(job_payload_file).read_text())
        if script_file:
            script = Path(script_file).read_text(encoding="utf-8")
        if script:
            job_payload = dict(job_payload or {})
            if job_payload.get("arguments"):
                raise ValueError("script/script_file cannot be combined with job_payload arguments.")
            job_payload["script"] = script
        serialized_job_payload = ""
        if job_payload:
            serialized_job_payload = json.dumps(job_payload)
            argparse_args.append(("job-payload-json", serialized_job_payload))
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
            "working_directory": launcher_working_directory or working_directory,
            "binary": launcher_binary,
            "argparse_args": argparse_args,
            "packages": list(self.DEFAULT_PACKAGES),
        }
        if repo:
            create_kwargs["repo"] = repo
        if branch:
            create_kwargs["branch"] = branch
        if launcher_script:
            create_kwargs["script"] = launcher_script
            create_kwargs["force_single_script_file"] = True
        else:
            create_kwargs["module"] = launcher_module

        task = Task.create(**create_kwargs)
        for param_name in ("bridge/auth_token", "Args/auth-token", "General/auth-token", "auth-token"):
            try:
                task.delete_parameter(param_name, force=True)
            except Exception:
                pass

        params_to_set: Dict[str, str] = {
            "Args/facility": selected_facility,
            "Args/system": selected_system,
            "Args/submit-path": selected_submit_path,
            "Args/status-path-template": selected_status_path_template,
            "Args/cancel-path-template": selected_cancel_path_template,
            "env:IRI_FACILITY": selected_facility,
            "env:IRI_API_BASE_URL": selected_api_base_url,
            "env:IRI_SYSTEM": selected_system,
            "env:IRI_SUBMIT_PATH": selected_submit_path,
            "env:IRI_STATUS_PATH_TEMPLATE": selected_status_path_template,
            "env:IRI_CANCEL_PATH_TEMPLATE": selected_cancel_path_template,
        }
        if resolved_resource_id:
            params_to_set["env:IRI_RESOURCE_ID"] = resolved_resource_id
        if result_path_template:
            params_to_set["Args/result-path-template"] = result_path_template
        if serialized_job_payload:
            params_to_set["Args/job-payload-json"] = serialized_job_payload
        task.set_parameters_as_dict(params_to_set)

        clearml_user_properties = dict(user_properties or {})
        if serialized_job_payload:
            clearml_user_properties.setdefault("iri_job_payload_json", serialized_job_payload)
        clearml_user_properties.setdefault("iri_facility", selected_facility)
        clearml_user_properties.setdefault("iri_system", selected_system)
        if resolved_resource_id:
            clearml_user_properties.setdefault("iri_resource_id", resolved_resource_id)
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


def _task_output_log_url(task: Task) -> str:
    try:
        app_server = (task.get_app_server() or "").rstrip("/")
    except Exception:
        app_server = ""
    task_id = getattr(task, "id", "") or ""
    project_id = getattr(task, "project", "") or ""
    if not app_server or not task_id or not project_id:
        return ""
    return f"{app_server}/projects/{project_id}/experiments/{task_id}/output/log"


def _build_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(
        description="Create and optionally enqueue a ClearML task that submits work to an IRI API."
    )
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--working-directory", default=".")
    parser.add_argument("--task-type", default=Task.TaskTypes.data_processing.value)
    parser.add_argument("--facility", required=True, choices=sorted(FACILITY_BASE_URLS))
    parser.add_argument("--system", required=True)
    parser.add_argument("--submit-path", default="/api/v1/compute/job/{system}")
    parser.add_argument("--status-path-template", default="/api/v1/compute/status/{system}/{job_id}")
    parser.add_argument("--cancel-path-template", default="/api/v1/compute/cancel/{system}/{job_id}")
    parser.add_argument("--result-path-template", default="")
    parser.add_argument("--method", default="POST")
    parser.add_argument("--job-payload-json", default="")
    parser.add_argument("--job-payload-file", default="")
    parser.add_argument("--script", default="")
    parser.add_argument("--script-file", default="")
    parser.add_argument("--headers-json", default="")
    parser.add_argument("--id-field", default="id")
    parser.add_argument("--status-field", default="status.state")
    parser.add_argument("--result-field", default="")
    parser.add_argument("--terminal-states-json", default="")
    parser.add_argument("--success-states-json", default="")
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--request-timeout-sec", type=int, default=60)
    parser.add_argument("--artifact-path", default="iri_result.json")
    parser.add_argument("--auth-header-name", default="Authorization")
    parser.add_argument("--auth-token-prefix", default="Bearer ")
    parser.add_argument("--queue", default="")
    parser.add_argument("--tags-json", default="")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    launcher = IRILauncher()
    if args.job_payload_json and args.job_payload_file:
        raise ValueError("Pass only one of --job-payload-json or --job-payload-file.")
    if args.script and args.script_file:
        raise ValueError("Pass only one of --script or --script-file.")
    job_payload = json.loads(args.job_payload_json) if args.job_payload_json else None
    headers = json.loads(args.headers_json) if args.headers_json else None
    terminal_states = json.loads(args.terminal_states_json) if args.terminal_states_json else None
    success_states = json.loads(args.success_states_json) if args.success_states_json else None
    tags = json.loads(args.tags_json) if args.tags_json else None

    task = launcher.create(
        project_name=args.project_name,
        task_name=args.task_name,
        repo=args.repo or None,
        branch=args.branch or None,
        working_directory=args.working_directory,
        task_type=_parse_task_type(args.task_type),
        facility=args.facility,
        system=args.system,
        submit_path=args.submit_path or None,
        status_path_template=args.status_path_template or None,
        cancel_path_template=args.cancel_path_template or None,
        result_path_template=args.result_path_template or "",
        method=args.method,
        job_payload=job_payload,
        job_payload_file=args.job_payload_file or None,
        script=args.script,
        script_file=args.script_file or None,
        headers=headers,
        id_field=args.id_field,
        status_field=args.status_field,
        result_field=args.result_field,
        terminal_states=terminal_states,
        success_states=success_states,
        poll_interval=args.poll_interval,
        timeout_sec=args.timeout_sec,
        request_timeout_sec=args.request_timeout_sec,
        artifact_path=args.artifact_path,
        auth_header_name=args.auth_header_name,
        auth_token_prefix=args.auth_token_prefix,
        tags=tags,
    )
    if args.queue:
        Task.enqueue(task, queue_name=args.queue)
        print(f"Enqueued task: {task.id} on queue {args.queue}")
    else:
        print(f"Created task: {task.id}")
    task_url = _task_output_log_url(task)
    if task_url:
        print(f"ClearML results page: {task_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
