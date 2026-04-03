import argparse
import atexit
import json
import os
import shlex
import signal
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from clearml import Task
from requests import HTTPError

from ._shared import (
    FACILITY_BASE_URLS,
    _combine_shell_text,
    _escape_graphql_string,
    _normalize_precommands,
    _normalize_script_text,
    clean_str,
)

_CANCEL_CONTEXT: Dict[str, Any] = {
    "armed": False,
    "session": None,
    "cancel_url": "",
    "headers": None,
    "request_timeout_sec": 0,
    "logger": None,
    "watcher_stop": None,
}
_CANCEL_FIRED = threading.Event()
_CANCEL_RESPONSE: Dict[str, Any] = {}
_PREVIOUS_SIGNAL_HANDLERS: Dict[int, Any] = {}


def resolve_artifact_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    try:
        base_dir = Path.cwd()
    except FileNotFoundError:
        base_dir = Path(tempfile.gettempdir())

    resolved = base_dir / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def parse_json_object(raw: str, arg_name: str) -> Dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{arg_name} must be a JSON object")
    return parsed


def parse_json_list(raw: str, arg_name: str, default: List[str]) -> List[str]:
    if not raw:
        return default
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError(f"{arg_name} must be a JSON list")
    return [str(item) for item in parsed]


def normalize_job_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    script = clean_str(normalized.pop("script", ""))
    script_path = clean_str(normalized.pop("script_path", ""))
    script_remote_path = clean_str(normalized.pop("script_remote_path", ""))
    command = clean_str(normalized.pop("command", ""))
    precommand = clean_str(normalized.pop("precommand", ""))
    precommands_raw = normalized.pop("precommands", [])
    if precommands_raw and not isinstance(precommands_raw, list):
        raise ValueError("Payload field 'precommands' must be a list of strings.")
    prelude = _normalize_precommands(precommand, precommands_raw or None)

    arguments = normalized.get("arguments")
    if arguments and (script or script_path or script_remote_path or command):
        raise ValueError("Payload cannot include both arguments and script/script_path/script_remote_path/command.")
    if script and (script_path or script_remote_path):
        raise ValueError("Payload cannot include both script and script_path/script_remote_path.")
    if script_path and script_remote_path:
        raise ValueError("Payload cannot include both script_path and script_remote_path.")

    if command:
        script = command
    remote_script_path = script_path or script_remote_path

    if remote_script_path:
        normalized.setdefault("executable", "/bin/bash")
        normalized["arguments"] = [
            "-c",
            _escape_graphql_string(
                _combine_shell_text(prelude, f"/bin/bash -l {shlex.quote(remote_script_path)}")
            ),
        ]
    elif script:
        normalized.setdefault("executable", "/bin/bash")
        normalized["arguments"] = ["-c", _escape_graphql_string(_combine_shell_text(prelude, _normalize_script_text(script)))]
    elif (
        normalized.get("executable") == "/bin/bash"
        and isinstance(arguments, list)
        and len(arguments) == 2
        and str(arguments[0]) in {"-lc", "-c"}
        and isinstance(arguments[1], str)
    ):
        normalized["arguments"] = [
            "-c",
            _escape_graphql_string(_combine_shell_text(prelude, _normalize_script_text(arguments[1]))),
        ]
    elif prelude:
        raise ValueError(
            "Payload field 'precommand' requires a shell-based payload using command, script, "
            "script_path, or executable=/bin/bash with arguments ['-c'|'-lc', ...]."
        )

    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-name",
        default=os.getenv("CLEARML_PROJECT_NAME", "amsc/pipeline-iri-bridge"),
    )
    parser.add_argument(
        "--task-name",
        default=os.getenv("CLEARML_TASK_NAME", "submit-iri-job"),
    )
    parser.add_argument(
        "--task-type",
        default=os.getenv("CLEARML_TASK_TYPE", "data_processing"),
    )
    parser.add_argument(
        "--facility",
        default=os.getenv("IRI_FACILITY", ""),
        help="Named IRI deployment to target: alcf, nersc, or olcf.",
    )
    parser.add_argument(
        "--system",
        default=os.getenv("IRI_SYSTEM", os.getenv("IRI_RESOURCE_ID", "")),
        help="Target system name or resource identifier used in /api/v1/compute/* paths.",
    )
    parser.add_argument(
        "--submit-path",
        default=os.getenv("IRI_SUBMIT_PATH", "/api/v1/compute/job/{system}"),
    )
    parser.add_argument(
        "--status-path-template",
        default=os.getenv("IRI_STATUS_PATH_TEMPLATE", "/api/v1/compute/status/{system}/{job_id}"),
    )
    parser.add_argument(
        "--cancel-path-template",
        default=os.getenv("IRI_CANCEL_PATH_TEMPLATE", "/api/v1/compute/cancel/{system}/{job_id}"),
    )
    parser.add_argument(
        "--result-path-template",
        default=os.getenv("IRI_RESULT_PATH_TEMPLATE", ""),
    )
    parser.add_argument(
        "--method",
        default=os.getenv("IRI_SUBMIT_METHOD", "POST"),
    )
    parser.add_argument("--job-payload-json", default=os.getenv("IRI_JOB_PAYLOAD_JSON", ""))
    parser.add_argument("--job-payload-file", default=os.getenv("IRI_JOB_PAYLOAD_FILE", ""))
    parser.add_argument("--script", default=os.getenv("IRI_JOB_SCRIPT", ""))
    parser.add_argument("--script-file", default=os.getenv("IRI_JOB_SCRIPT_FILE", ""))
    parser.add_argument("--headers-json", default=os.getenv("IRI_HEADERS_JSON", ""))
    parser.add_argument(
        "--id-field",
        default=os.getenv("IRI_JOB_ID_FIELD", "id"),
        help="Dot path for job id, e.g. id or data.job_id",
    )
    parser.add_argument(
        "--status-field",
        default=os.getenv("IRI_STATUS_FIELD", "status.state"),
        help="Dot path for status, e.g. status.state or data.state",
    )
    parser.add_argument(
        "--result-field",
        default=os.getenv("IRI_RESULT_FIELD", ""),
        help="Optional dot path for a result value in the final response payload.",
    )
    parser.add_argument(
        "--terminal-states-json",
        default=os.getenv(
            "IRI_TERMINAL_STATES_JSON",
            '["COMPLETED","FAILED","CANCELED"]',
        ),
    )
    parser.add_argument(
        "--success-states-json",
        default=os.getenv("IRI_SUCCESS_STATES_JSON", '["COMPLETED"]'),
    )
    parser.add_argument("--poll-interval", type=int, default=int(os.getenv("IRI_POLL_INTERVAL", "10")))
    parser.add_argument("--timeout-sec", type=int, default=int(os.getenv("IRI_TIMEOUT_SEC", "1800")))
    parser.add_argument(
        "--request-timeout-sec",
        type=int,
        default=int(os.getenv("IRI_REQUEST_TIMEOUT_SEC", "60")),
    )
    parser.add_argument(
        "--log-stdout",
        action="store_true",
        default=os.getenv("IRI_LOG_STDOUT", "1") != "0",
    )
    parser.add_argument(
        "--log-stderr",
        action="store_true",
        default=os.getenv("IRI_LOG_STDERR", "1") != "0",
    )
    parser.add_argument(
        "--max-log-chars",
        type=int,
        default=int(os.getenv("IRI_MAX_LOG_CHARS", "20000")),
    )
    parser.add_argument("--artifact-path", default=os.getenv("IRI_ARTIFACT_PATH", "iri_result.json"))
    parser.add_argument(
        "--auth-token",
        default=os.getenv("IRI_API_TOKEN", ""),
        help="Token value only; prefix is controlled by --auth-token-prefix",
    )
    parser.add_argument(
        "--auth-header-name",
        default=os.getenv("IRI_AUTH_HEADER_NAME", "Authorization"),
    )
    parser.add_argument(
        "--auth-token-prefix",
        default=os.getenv("IRI_AUTH_TOKEN_PREFIX", "Bearer "),
    )
    return parser.parse_args()


def resolve_api_base_url(facility: str) -> str:
    normalized = clean_str(facility).lower()
    if not normalized:
        raise ValueError(
            "IRI facility is required. Pass --facility alcf|nersc|olcf or export IRI_FACILITY."
        )
    if normalized == "custom":
        url = clean_str(os.getenv("IRI_API_BASE_URL", ""))
        if not url:
            raise ValueError(
                "facility='custom' requires IRI_API_BASE_URL to be set in the environment."
            )
        return url
    if normalized not in FACILITY_BASE_URLS:
        supported = ", ".join(sorted(FACILITY_BASE_URLS))
        raise ValueError(f"Unsupported facility '{normalized}'. Use one of: {supported}.")
    return FACILITY_BASE_URLS[normalized]


def read_nested(payload: Dict[str, Any], dot_path: str) -> Any:
    if not dot_path:
        return None
    cur: Any = payload
    for token in dot_path.split("."):
        if not isinstance(cur, dict) or token not in cur:
            return None
        cur = cur[token]
    return cur


def _get_task_parameter(task: Task, *names: str) -> str:
    try:
        params = task.get_parameters_as_dict()
    except Exception:
        params = {}
    try:
        flat_params = task.get_parameters()
    except Exception:
        flat_params = {}

    def _lookup(mapping: Dict[str, Any], name: str) -> str:
        if not isinstance(mapping, dict):
            return ""
        value = mapping.get(name)
        normalized = clean_str(value)
        if normalized:
            return normalized
        if "/" in name:
            head, tail = name.split("/", 1)
            section = mapping.get(head)
            if isinstance(section, dict):
                normalized = clean_str(section.get(tail))
                if normalized:
                    return normalized
        return ""

    for name in names:
        normalized = _lookup(params, name)
        if normalized:
            return normalized
        normalized = _lookup(flat_params, name)
        if normalized:
            return normalized
    return ""


def read_payload(args: argparse.Namespace, task: Optional[Task] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if args.job_payload_file:
        payload = json.loads(Path(args.job_payload_file).read_text())
    elif args.job_payload_json:
        payload = parse_json_object(args.job_payload_json, "--job-payload-json")
    if task is not None:
        task_payload = _get_task_parameter(
            task,
            "Args/job-payload-json",
            "job-payload-json",
            "job_payload_json",
        )
        if task_payload:
            payload = parse_json_object(task_payload, "Args/job-payload-json")

    script = clean_str(args.script)
    script_file = clean_str(args.script_file)
    if script and script_file:
        raise ValueError("Pass only one of --script or --script-file.")
    if script_file:
        script = Path(script_file).read_text(encoding="utf-8")
    if script:
        payload = dict(payload)
        payload["script"] = script

    return normalize_job_payload(payload)


def build_headers(args: argparse.Namespace) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update({str(k): str(v) for k, v in parse_json_object(args.headers_json, "--headers-json").items()})
    token = clean_str(args.auth_token)
    if token:
        headers[args.auth_header_name] = f"{args.auth_token_prefix}{token}"
    return headers


def validate_auth(headers: Dict[str, str], args: argparse.Namespace) -> None:
    auth_header_name = clean_str(args.auth_header_name) or "Authorization"
    auth_value = clean_str(headers.get(auth_header_name))
    if not auth_value:
        raise ValueError(
            "Missing IRI API token. Set IRI_API_TOKEN or pass --auth-token so the "
            f"request can include the '{auth_header_name}' header."
        )


def parse_job_id(submit_response: Dict[str, Any], id_field: str) -> str:
    value = read_nested(submit_response, id_field)
    normalized = clean_str(value)
    if not normalized:
        raise ValueError(f"Could not find job id using id_field='{id_field}' in {submit_response}")
    return normalized


def parse_status(payload: Dict[str, Any], status_field: str) -> str:
    return clean_str(read_nested(payload, status_field)).upper()


def parse_exit_code(payload: Dict[str, Any]) -> Optional[int]:
    candidates = (
        read_nested(payload, "status.exit_code"),
        payload.get("exit_code") if isinstance(payload, dict) else None,
    )
    for value in candidates:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


_SCRUB_PARAM_BASE_NAMES = {
    "artifact_path",
    "auth_header_name",
    "auth_token",
    "auth_token_prefix",
    "cancel_path_template",
    "headers_json",
    "id_field",
    "job_payload_file",
    "job_payload_json",
    "log_stderr",
    "log_stdout",
    "max_log_chars",
    "poll_interval",
    "project_name",
    "request_timeout_sec",
    "result_field",
    "result_path_template",
    "script_file",
    "status_field",
    "status_path_template",
    "submit_path",
    "success_states_json",
    "task_name",
    "task_type",
    "terminal_states_json",
    "timeout_sec",
}


def scrub_task_parameters(task: Task) -> None:
    to_scrub = ["bridge/auth_token"]
    for name in _SCRUB_PARAM_BASE_NAMES:
        to_scrub.append(name)
        to_scrub.append(f"Args/{name}")
        to_scrub.append(f"General/{name}")
    for param_name in to_scrub:
        try:
            task.delete_parameter(param_name, force=True)
        except Exception:
            pass


def report_job_output(logger: Any, label: str, file_path: str, max_chars: int) -> None:
    normalized_path = clean_str(file_path)
    if not normalized_path:
        logger.report_text(f"[iri] {label}_path missing in payload")
        return
    path = Path(normalized_path)
    if not path.exists():
        logger.report_text(f"[iri] {label}_path not found: {normalized_path}")
        return
    content = path.read_text(encoding="utf-8", errors="replace")
    truncated = False
    if max_chars > 0 and len(content) > max_chars:
        content = content[-max_chars:]
        truncated = True
    header = f"[iri] {label} from {normalized_path}"
    if truncated:
        header += f" (last {max_chars} chars)"
    logger.report_text(f"{header}\n{content}")


def upload_job_output_artifact(task: Task, logger: Any, label: str, file_path: str) -> None:
    normalized_path = clean_str(file_path)
    if not normalized_path:
        return
    path = Path(normalized_path)
    if not path.exists():
        logger.report_text(f"[iri] skipping {label} artifact upload; file not found: {normalized_path}")
        return
    task.upload_artifact(name=f"iri_{label}", artifact_object=str(path))
    logger.report_text(f"[iri] uploaded artifact iri_{label} from {normalized_path}")


def make_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def format_path_template(template: str, **values: str) -> str:
    try:
        return template.format(**values)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(
            f"Missing path parameter '{missing}' required by template '{template}'"
        ) from exc


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    request_timeout_sec: int,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = session.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        timeout=request_timeout_sec,
    )
    try:
        response.raise_for_status()
    except HTTPError as exc:
        detail = response.text.strip()
        if len(detail) > 4000:
            detail = detail[:4000] + "...<truncated>"
        message = (
            f"{exc}\n"
            f"Response body: {detail or '<empty>'}"
        )
        raise HTTPError(message, response=response) from exc
    if not response.text:
        return {}
    parsed = response.json()
    if not isinstance(parsed, dict):
        return {"raw": parsed}
    return parsed


def add_query_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def request_data(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    request_timeout_sec: int,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    response = session.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        timeout=request_timeout_sec,
    )
    try:
        response.raise_for_status()
    except HTTPError as exc:
        detail = response.text.strip()
        if len(detail) > 4000:
            detail = detail[:4000] + "...<truncated>"
        message = (
            f"{exc}\n"
            f"Response body: {detail or '<empty>'}"
        )
        raise HTTPError(message, response=response) from exc
    if not response.text:
        return {}
    return response.json()


def _cancel_watcher_loop(task: Task, stop_event: threading.Event, check_interval: float) -> None:
    """Daemon thread: polls ClearML task status and fires cancel when the task is stopped."""
    while not stop_event.wait(check_interval):
        if not _CANCEL_CONTEXT.get("armed"):
            return
        try:
            remote_task = Task.get_task(task_id=task.id)
            task_status = clean_str(remote_task.get_status()).lower()
        except Exception:
            continue
        if task_status in {"stopped", "stopping"}:
            _fire_remote_cancel(f"cancel watcher: ClearML task status={task_status}")
            return


def _atexit_cancel() -> None:
    """Last-resort cancel: fires if the process exits before cancel was sent."""
    _fire_remote_cancel("atexit: process exiting before cancel was sent")


def _arm_cancel_handler(
    *,
    task: Task,
    session: requests.Session,
    cancel_url: str,
    headers: Dict[str, str],
    request_timeout_sec: int,
    logger: Any,
    cancel_check_interval: float = 3.0,
) -> None:
    global _CANCEL_RESPONSE
    _CANCEL_FIRED.clear()
    _CANCEL_RESPONSE = {}
    stop_event = threading.Event()
    _CANCEL_CONTEXT.update(
        {
            "armed": True,
            "session": session,
            "cancel_url": cancel_url,
            "headers": dict(headers),
            "request_timeout_sec": request_timeout_sec,
            "logger": logger,
            "watcher_stop": stop_event,
        }
    )
    watcher = threading.Thread(
        target=_cancel_watcher_loop,
        args=(task, stop_event, cancel_check_interval),
        daemon=True,
        name="iri-cancel-watcher",
    )
    watcher.start()
    for sig in (signal.SIGTERM, signal.SIGINT):
        if sig not in _PREVIOUS_SIGNAL_HANDLERS:
            _PREVIOUS_SIGNAL_HANDLERS[sig] = signal.getsignal(sig)
        signal.signal(sig, _handle_termination_signal)
    atexit.register(_atexit_cancel)


def _disarm_cancel_handler() -> None:
    atexit.unregister(_atexit_cancel)
    stop_event = _CANCEL_CONTEXT.get("watcher_stop")
    if stop_event is not None:
        stop_event.set()
    _CANCEL_CONTEXT.update(
        {
            "armed": False,
            "session": None,
            "cancel_url": "",
            "headers": None,
            "request_timeout_sec": 0,
            "logger": None,
            "watcher_stop": None,
        }
    )
    for sig, handler in list(_PREVIOUS_SIGNAL_HANDLERS.items()):
        try:
            signal.signal(sig, handler)
        except Exception:
            pass
        _PREVIOUS_SIGNAL_HANDLERS.pop(sig, None)


def _fire_remote_cancel(reason: str) -> Dict[str, Any]:
    global _CANCEL_RESPONSE
    if not _CANCEL_CONTEXT.get("armed") or _CANCEL_FIRED.is_set():
        return {}
    _CANCEL_FIRED.set()
    session = _CANCEL_CONTEXT.get("session")
    cancel_url = clean_str(_CANCEL_CONTEXT.get("cancel_url"))
    headers = _CANCEL_CONTEXT.get("headers") or {}
    request_timeout_sec = int(_CANCEL_CONTEXT.get("request_timeout_sec") or 0)
    logger = _CANCEL_CONTEXT.get("logger")
    if not session or not cancel_url:
        return {}
    if logger is not None:
        try:
            logger.report_text(f"[iri] {reason}; forwarding cancel to {cancel_url}")
        except Exception:
            pass
    try:
        payload = request_json(
            session=session,
            method="DELETE",
            url=cancel_url,
            headers=headers,
            request_timeout_sec=request_timeout_sec,
        )
    except Exception as exc:
        if logger is not None:
            try:
                logger.report_text(f"[iri] cancel request failed: {exc}")
            except Exception:
                pass
        _CANCEL_RESPONSE = {"error": str(exc)}
        return _CANCEL_RESPONSE
    if logger is not None:
        try:
            logger.report_text(f"[iri] cancel response={json.dumps(payload, sort_keys=True)}")
        except Exception:
            pass
    _CANCEL_RESPONSE = payload
    return payload


def _handle_termination_signal(signum: int, _frame: Any) -> None:
    signal_name = getattr(signal.Signals(signum), "name", str(signum))
    _fire_remote_cancel(f"received {signal_name}")
    raise SystemExit(128 + int(signum))


def _extract_resource_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("resources", "items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def resolve_system_identifier(
    facility: str,
    system: str,
    api_base_url: str,
    session: requests.Session,
    headers: Dict[str, str],
    request_timeout_sec: int,
) -> str:
    if clean_str(facility).lower() != "alcf":
        return system
    if "-" in system and len(system) >= 16:
        return system

    resources_url = make_url(api_base_url, "/api/v1/status/resources?resource_type=compute")
    payload = request_data(
        session=session,
        method="GET",
        url=resources_url,
        headers=headers,
        request_timeout_sec=request_timeout_sec,
    )
    items = _extract_resource_items(payload)
    target = system.strip().lower()

    for item in items:
        candidates = [
            clean_str(item.get("id")),
            clean_str(item.get("name")),
            clean_str(item.get("group")),
            clean_str(item.get("description")),
        ]
        if any(candidate.lower() == target for candidate in candidates if candidate):
            resolved = clean_str(item.get("id"))
            if resolved:
                return resolved

    for item in items:
        candidates = [
            clean_str(item.get("name")),
            clean_str(item.get("group")),
            clean_str(item.get("description")),
        ]
        if any(target in candidate.lower() for candidate in candidates if candidate):
            resolved = clean_str(item.get("id"))
            if resolved:
                return resolved

    raise ValueError(
        f"Could not resolve ALCF system '{system}' to a compute resource id via {resources_url}."
    )


def poll_until_terminal(
    session: requests.Session,
    status_url: str,
    cancel_url: str,
    headers: Dict[str, str],
    request_timeout_sec: int,
    status_field: str,
    terminal_states: List[str],
    timeout_sec: int,
    poll_interval: int,
    task: Task,
    logger: Any,
) -> Tuple[str, Dict[str, Any], float, bool]:
    start = time.time()
    last_payload: Dict[str, Any] = {}
    terminal_set = {s.upper() for s in terminal_states}
    historical_status_url = add_query_params(status_url, historical="true")
    while True:
        elapsed = time.time() - start
        if elapsed > timeout_sec:
            raise TimeoutError(
                f"Timeout waiting for terminal state after {timeout_sec}s. Last payload: {last_payload}"
            )

        # Check ClearML task status directly (belt and suspenders alongside watcher thread)
        try:
            remote_task = Task.get_task(task_id=task.id)
            task_status = clean_str(remote_task.get_status()).lower()
            if task_status in {"stopped", "stopping"}:
                _fire_remote_cancel(f"poll loop: ClearML task status={task_status}")
        except Exception:
            pass

        if _CANCEL_FIRED.is_set():
            return "CANCELED", {**last_payload, "clearml_cancel_response": _CANCEL_RESPONSE}, elapsed, True

        try:
            last_payload = request_json(
                session=session,
                method="GET",
                url=status_url,
                headers=headers,
                request_timeout_sec=request_timeout_sec,
            )
        except HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code not in {400, 404}:
                raise
            logger.report_text(
                f"[iri] live status lookup failed with {status_code}; retrying historical status endpoint"
            )
            last_payload = request_json(
                session=session,
                method="GET",
                url=historical_status_url,
                headers=headers,
                request_timeout_sec=request_timeout_sec,
            )
        status = parse_status(last_payload, status_field)
        logger.report_text(f"[iri] status={status or '<missing>'} elapsed={elapsed:.1f}s")
        logger.report_scalar("iri_bridge", "wait_time_sec", value=elapsed, iteration=int(elapsed))
        if status and status in terminal_set:
            return status, last_payload, elapsed, False
        time.sleep(max(1, poll_interval))


def main() -> None:
    args = parse_args()
    project_name = clean_str(args.project_name) or "amsc/pipeline-iri-bridge"
    task_name = clean_str(args.task_name) or "submit-iri-job"
    api_base_url = resolve_api_base_url(args.facility)
    task = Task.init(
        project_name=project_name,
        task_name=task_name,
        task_type=clean_str(args.task_type) or "data_processing",
    )
    scrub_task_parameters(task)
    logger = task.get_logger()

    payload_source = "cli"
    if not args.job_payload_json and not args.job_payload_file:
        payload_source = "task-parameters"
    payload = read_payload(args, task=task)
    headers = build_headers(args)
    validate_auth(headers, args)
    terminal_states = parse_json_list(
        args.terminal_states_json,
        "--terminal-states-json",
        default=["COMPLETED", "FAILED", "CANCELED"],
    )
    success_states = {
        s.upper()
        for s in parse_json_list(
            args.success_states_json,
            "--success-states-json",
            default=["COMPLETED"],
        )
    }
    system = clean_str(args.system)
    if not system:
        raise ValueError("IRI system is required. Pass --system or export IRI_SYSTEM.")

    session = requests.Session()
    resolved_system = resolve_system_identifier(
        facility=args.facility,
        system=system,
        api_base_url=api_base_url,
        session=session,
        headers=headers,
        request_timeout_sec=args.request_timeout_sec,
    )

    submit_url = make_url(
        api_base_url,
        format_path_template(args.submit_path, system=resolved_system, resource_id=resolved_system),
    )

    logger.report_text(f"[iri] submit_url={submit_url}")
    logger.report_text(f"[iri] auth_header_present={args.auth_header_name in headers}")
    logger.report_text(f"[iri] system={system} resolved_system={resolved_system}")
    logger.report_text(f"[iri] payload_source={payload_source}")
    logger.report_text(f"[iri] payload={json.dumps(payload, sort_keys=True)}")
    submit_response = request_json(
        session=session,
        method=args.method.upper(),
        url=submit_url,
        headers=headers,
        request_timeout_sec=args.request_timeout_sec,
        payload=payload if args.method.upper() in {"POST", "PUT", "PATCH"} else None,
    )
    logger.report_text(f"[iri] submit_response={json.dumps(submit_response, sort_keys=True)}")
    job_id = parse_job_id(submit_response, args.id_field)
    logger.report_text(f"[iri] job_id={job_id}")

    status_url = make_url(
        api_base_url,
        format_path_template(
            args.status_path_template,
            system=resolved_system,
            resource_id=resolved_system,
            job_id=job_id,
        ),
    )
    cancel_url = make_url(
        api_base_url,
        format_path_template(
            args.cancel_path_template,
            system=resolved_system,
            resource_id=resolved_system,
            job_id=job_id,
        ),
    )
    _arm_cancel_handler(
        task=task,
        session=session,
        cancel_url=cancel_url,
        headers=headers,
        request_timeout_sec=args.request_timeout_sec,
        logger=logger,
    )
    try:
        status, status_payload, elapsed, clearml_cancel_requested = poll_until_terminal(
            session=session,
            status_url=status_url,
            cancel_url=cancel_url,
            headers=headers,
            request_timeout_sec=args.request_timeout_sec,
            status_field=args.status_field,
            terminal_states=terminal_states,
            timeout_sec=args.timeout_sec,
            poll_interval=args.poll_interval,
            task=task,
            logger=logger,
        )
    finally:
        _disarm_cancel_handler()

    final_payload = status_payload
    if args.result_path_template:
        result_url = make_url(
            api_base_url,
            format_path_template(
                args.result_path_template,
                system=resolved_system,
                resource_id=resolved_system,
                job_id=job_id,
            ),
        )
        final_payload = request_json(
            session=session,
            method="GET",
            url=result_url,
            headers=headers,
            request_timeout_sec=args.request_timeout_sec,
        )

    result_value = read_nested(final_payload, args.result_field) if args.result_field else None
    exit_code = parse_exit_code(status_payload)
    output = {
        "system": system,
        "resolved_system": resolved_system,
        "resource_id": resolved_system,
        "job_id": job_id,
        "status": status,
        "exit_code": exit_code,
        "elapsed_sec": elapsed,
        "submit_response": submit_response,
        "status_response": status_payload,
        "final_response": final_payload,
        "result_value": result_value,
        "clearml_cancel_requested": clearml_cancel_requested,
    }
    artifact_path = resolve_artifact_path(args.artifact_path)
    artifact_path.write_text(json.dumps(output, indent=2, sort_keys=True))
    task.upload_artifact(name="iri_result", artifact_object=str(artifact_path))
    upload_job_output_artifact(
        task=task,
        logger=logger,
        label="stdout",
        file_path=clean_str(payload.get("stdout_path")),
    )
    upload_job_output_artifact(
        task=task,
        logger=logger,
        label="stderr",
        file_path=clean_str(payload.get("stderr_path")),
    )
    logger.report_scalar("iri_bridge", "total_time_sec", value=elapsed, iteration=0)
    if args.log_stdout:
        report_job_output(
            logger=logger,
            label="stdout",
            file_path=clean_str(payload.get("stdout_path")),
            max_chars=args.max_log_chars,
        )
    if args.log_stderr:
        report_job_output(
            logger=logger,
            label="stderr",
            file_path=clean_str(payload.get("stderr_path")),
            max_chars=args.max_log_chars,
        )

    if exit_code is not None:
        logger.report_text(f"[iri] exit_code={exit_code}")

    if clearml_cancel_requested:
        logger.report_text("[iri] remote job cancel was triggered by a ClearML stop request")
        return

    if status not in success_states or (exit_code is not None and exit_code != 0):
        reason = f"status='{status}'"
        if exit_code is not None:
            reason += f", exit_code={exit_code}"
        try:
            task.mark_failed(status_reason=f"IRI job finished with {reason}")
        except Exception:
            pass
        raise RuntimeError(f"IRI job failed with {reason}. Output: {output}")

    logger.report_text(f"[iri] completed status={status} elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
