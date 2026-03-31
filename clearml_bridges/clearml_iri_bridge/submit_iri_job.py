import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from clearml import Task

FACILITY_BASE_URLS = {
    "alcf": "https://api.alcf.anl.gov",
    "nersc": "https://api.nersc.gov",
    "olcf": "https://s3m.olcf.ornl.gov",
}


def clean_str(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null"}:
        return ""
    return normalized


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-name", "--project_name",
        default=os.getenv("CLEARML_PROJECT_NAME", "amsc/pipeline-iri-bridge"),
    )
    parser.add_argument(
        "--task-name", "--task_name",
        default=os.getenv("CLEARML_TASK_NAME", "submit-iri-job"),
    )
    parser.add_argument(
        "--task-type", "--task_type",
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
        "--submit-path", "--submit_path",
        default=os.getenv("IRI_SUBMIT_PATH", "/api/v1/compute/job/{system}"),
    )
    parser.add_argument(
        "--status-path-template", "--status_path_template",
        default=os.getenv("IRI_STATUS_PATH_TEMPLATE", "/api/v1/compute/status/{system}/{job_id}"),
    )
    parser.add_argument(
        "--result-path-template", "--result_path_template",
        default=os.getenv("IRI_RESULT_PATH_TEMPLATE", ""),
    )
    parser.add_argument(
        "--method",
        default=os.getenv("IRI_SUBMIT_METHOD", "POST"),
    )
    parser.add_argument("--job-payload-json", "--job_payload_json", default=os.getenv("IRI_JOB_PAYLOAD_JSON", ""))
    parser.add_argument("--job-payload-file", "--job_payload_file", default=os.getenv("IRI_JOB_PAYLOAD_FILE", ""))
    parser.add_argument("--headers-json", "--headers_json", default=os.getenv("IRI_HEADERS_JSON", ""))
    parser.add_argument(
        "--id-field", "--id_field",
        default=os.getenv("IRI_JOB_ID_FIELD", "id"),
        help="Dot path for job id, e.g. id or data.job_id",
    )
    parser.add_argument(
        "--status-field", "--status_field",
        default=os.getenv("IRI_STATUS_FIELD", "status.state"),
        help="Dot path for status, e.g. status.state or data.state",
    )
    parser.add_argument(
        "--result-field", "--result_field",
        default=os.getenv("IRI_RESULT_FIELD", ""),
        help="Optional dot path for a result value in the final response payload.",
    )
    parser.add_argument(
        "--terminal-states-json", "--terminal_states_json",
        default=os.getenv(
            "IRI_TERMINAL_STATES_JSON",
            '["COMPLETED","FAILED","CANCELED"]',
        ),
    )
    parser.add_argument(
        "--success-states-json", "--success_states_json",
        default=os.getenv("IRI_SUCCESS_STATES_JSON", '["COMPLETED"]'),
    )
    parser.add_argument("--poll-interval", "--poll_interval", type=int, default=int(os.getenv("IRI_POLL_INTERVAL", "10")))
    parser.add_argument("--timeout-sec", "--timeout_sec", type=int, default=int(os.getenv("IRI_TIMEOUT_SEC", "1800")))
    parser.add_argument(
        "--request-timeout-sec", "--request_timeout_sec",
        type=int,
        default=int(os.getenv("IRI_REQUEST_TIMEOUT_SEC", "60")),
    )
    parser.add_argument("--artifact-path", "--artifact_path", default=os.getenv("IRI_ARTIFACT_PATH", "iri_result.json"))
    parser.add_argument(
        "--auth-token", "--auth_token",
        default=os.getenv("IRI_API_TOKEN", ""),
        help="Token value only; prefix is controlled by --auth-token-prefix",
    )
    parser.add_argument(
        "--auth-header-name", "--auth_header_name",
        default=os.getenv("IRI_AUTH_HEADER_NAME", "Authorization"),
    )
    parser.add_argument(
        "--auth-token-prefix", "--auth_token_prefix",
        default=os.getenv("IRI_AUTH_TOKEN_PREFIX", "Bearer "),
    )
    return parser.parse_args()


def resolve_api_base_url(facility: str) -> str:
    normalized = clean_str(facility).lower()
    if not normalized:
        raise ValueError(
            "IRI facility is required. Pass --facility alcf|nersc|olcf or export IRI_FACILITY."
        )
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


def read_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.job_payload_file:
        return json.loads(Path(args.job_payload_file).read_text())
    return parse_json_object(args.job_payload_json, "--job-payload-json")


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


def parse_job_id(submit_response: Dict[str, Any], id_field: str) -> str:
    value = read_nested(submit_response, id_field)
    normalized = clean_str(value)
    if not normalized:
        raise ValueError(f"Could not find job id using id_field='{id_field}' in {submit_response}")
    return normalized


def parse_status(payload: Dict[str, Any], status_field: str) -> str:
    return clean_str(read_nested(payload, status_field)).upper()


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
    response.raise_for_status()
    if not response.text:
        return {}
    parsed = response.json()
    if not isinstance(parsed, dict):
        return {"raw": parsed}
    return parsed


def poll_until_terminal(
    session: requests.Session,
    status_url: str,
    headers: Dict[str, str],
    request_timeout_sec: int,
    status_field: str,
    terminal_states: List[str],
    timeout_sec: int,
    poll_interval: int,
    logger: Any,
) -> Tuple[str, Dict[str, Any], float]:
    start = time.time()
    last_payload: Dict[str, Any] = {}
    terminal_set = {s.upper() for s in terminal_states}
    while True:
        elapsed = time.time() - start
        if elapsed > timeout_sec:
            raise TimeoutError(
                f"Timeout waiting for terminal state after {timeout_sec}s. Last payload: {last_payload}"
            )

        last_payload = request_json(
            session=session,
            method="GET",
            url=status_url,
            headers=headers,
            request_timeout_sec=request_timeout_sec,
        )
        status = parse_status(last_payload, status_field)
        logger.report_text(f"[iri] status={status or '<missing>'} elapsed={elapsed:.1f}s")
        logger.report_scalar("iri_bridge", "wait_time_sec", value=elapsed, iteration=int(elapsed))
        if status and status in terminal_set:
            return status, last_payload, elapsed
        time.sleep(max(1, poll_interval))


def main() -> None:
    args = parse_args()
    project_name = clean_str(args.project_name) or "amsc/pipeline-iri-bridge"
    task_name = clean_str(args.task_name) or "submit-iri-job"
    api_base_url = resolve_api_base_url(args.facility)
    print("Selected IRI API base URL:", api_base_url)
    task = Task.init(
        project_name=project_name,
        task_name=task_name,
        task_type=clean_str(args.task_type) or "data_processing",
    )
    logger = task.get_logger()

    payload = read_payload(args)
    headers = build_headers(args)
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

    submit_url = make_url(
        api_base_url,
        format_path_template(args.submit_path, system=system, resource_id=system),
    )
    session = requests.Session()

    logger.report_text(f"[iri] submit_url={submit_url}")
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
            system=system,
            resource_id=system,
            job_id=job_id,
        ),
    )
    status, status_payload, elapsed = poll_until_terminal(
        session=session,
        status_url=status_url,
        headers=headers,
        request_timeout_sec=args.request_timeout_sec,
        status_field=args.status_field,
        terminal_states=terminal_states,
        timeout_sec=args.timeout_sec,
        poll_interval=args.poll_interval,
        logger=logger,
    )

    final_payload = status_payload
    if args.result_path_template:
        result_url = make_url(
            api_base_url,
            format_path_template(
                args.result_path_template,
                system=system,
                resource_id=system,
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
    output = {
        "system": system,
        "resource_id": system,
        "job_id": job_id,
        "status": status,
        "elapsed_sec": elapsed,
        "submit_response": submit_response,
        "status_response": status_payload,
        "final_response": final_payload,
        "result_value": result_value,
    }
    artifact_path = Path(args.artifact_path)
    artifact_path.write_text(json.dumps(output, indent=2, sort_keys=True))
    task.upload_artifact(name="iri_result", artifact_object=str(artifact_path))
    logger.report_scalar("iri_bridge", "total_time_sec", value=elapsed, iteration=0)

    if status not in success_states:
        raise RuntimeError(f"IRI job failed with status '{status}'. Output: {output}")

    logger.report_text(f"[iri] completed status={status} elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
