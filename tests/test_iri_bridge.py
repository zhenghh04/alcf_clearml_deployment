from unittest.mock import MagicMock

import pytest

from clearml_iri_bridge.iri_launcher import IRILauncher
from clearml_iri_bridge.submit_iri_job import (
    build_headers,
    format_path_template,
    make_url,
    parse_job_id,
    parse_json_list,
    parse_json_object,
    parse_status,
    poll_until_terminal,
    read_nested,
)


def test_parse_json_object_requires_mapping() -> None:
    with pytest.raises(ValueError):
        parse_json_object('["not-an-object"]', "--job-payload-json")


def test_parse_json_list_defaults_and_casts() -> None:
    assert parse_json_list("", "--terminal-states-json", default=["DONE"]) == ["DONE"]
    assert parse_json_list('["ok", 3]', "--terminal-states-json", default=[]) == ["ok", "3"]


def test_read_nested_and_parse_helpers() -> None:
    payload = {"data": {"job_id": "abc-123", "state": "running"}}
    assert read_nested(payload, "data.job_id") == "abc-123"
    assert parse_job_id(payload, "data.job_id") == "abc-123"
    assert parse_status(payload, "data.state") == "RUNNING"


def test_build_headers_includes_auth_token() -> None:
    args = MagicMock(
        headers_json='{"X-Client":"clearml-iri-bridge"}',
        auth_token="secret-token",
        auth_header_name="Authorization",
        auth_token_prefix="Bearer ",
    )
    headers = build_headers(args)
    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["X-Client"] == "clearml-iri-bridge"


def test_make_url_normalizes_slashes() -> None:
    assert make_url("https://example.org/api", "/jobs/123") == "https://example.org/api/jobs/123"


def test_format_path_template_uses_resource_and_job_ids() -> None:
    path = format_path_template(
        "/api/v1/compute/status/{resource_id}/{job_id}",
        resource_id="aurora",
        job_id="job-123",
    )
    assert path == "/api/v1/compute/status/aurora/job-123"


def test_format_cancel_path_template_uses_resource_and_job_ids() -> None:
    path = format_path_template(
        "/api/v1/compute/cancel/{resource_id}/{job_id}",
        resource_id="aurora",
        job_id="job-123",
    )
    assert path == "/api/v1/compute/cancel/aurora/job-123"


def test_poll_until_terminal_cancels_remote_job_when_clearml_task_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str]] = []

    def fake_request_json(**kwargs):
        events.append((kwargs["method"], kwargs["url"]))
        if kwargs["method"] == "DELETE":
            return {"canceled": True}
        raise AssertionError("GET status should not be called after stop is detected")

    stopped_task = MagicMock()
    stopped_task.get_status.return_value = "stopped"

    monkeypatch.setattr(
        "clearml_iri_bridge.submit_iri_job.request_json",
        fake_request_json,
    )
    monkeypatch.setattr(
        "clearml_iri_bridge.submit_iri_job.Task.get_task",
        lambda task_id: stopped_task,
    )

    logger = MagicMock()
    status, payload, elapsed, canceled = poll_until_terminal(
        session=MagicMock(),
        status_url="https://api.example.org/status/job-123",
        cancel_url="https://api.example.org/cancel/job-123",
        headers={"Authorization": "Bearer token"},
        request_timeout_sec=5,
        status_field="status.state",
        terminal_states=["COMPLETED", "FAILED", "CANCELED"],
        timeout_sec=30,
        poll_interval=1,
        task=MagicMock(id="task-123"),
        logger=logger,
    )

    assert status == "CANCELED"
    assert canceled is True
    assert payload["clearml_cancel_response"] == {"canceled": True}
    assert elapsed >= 0
    assert events == [("DELETE", "https://api.example.org/cancel/job-123")]


def test_launcher_create_sets_expected_clearml_task(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, object] = {}
    fake_task = MagicMock()
    fake_task.delete_parameter = MagicMock()
    fake_task.set_parameters_as_dict = MagicMock()

    def fake_create(**kwargs):
        created.update(kwargs)
        return fake_task

    monkeypatch.setattr("clearml_iri_bridge.iri_launcher.Task.create", fake_create)

    launcher = IRILauncher()
    launcher.create(
        project_name="AmSC/pipeline-iri-bridge",
        task_name="submit-iri-job",
        repo="https://example.org/repo.git",
        branch="main",
        working_directory=".",
        facility="alcf",
        api_base_url="https://api.example.org",
        system="aurora",
        submit_path="/api/v1/compute/job/{system}",
        status_path_template="/api/v1/compute/status/{system}/{job_id}",
        cancel_path_template="/api/v1/compute/cancel/{system}/{job_id}",
        job_payload={"executable": "/bin/bash", "arguments": ["-lc", "echo hello"]},
        headers={"X-Client": "clearml-iri-bridge"},
        tags=["iri-bridge"],
    )

    argparse_args = dict(created["argparse_args"])
    assert created["packages"] == IRILauncher.DEFAULT_PACKAGES
    assert argparse_args["facility"] == "alcf"
    assert argparse_args["system"] == "aurora"
    assert argparse_args["cancel-path-template"] == "/api/v1/compute/cancel/{system}/{job_id}"
    assert argparse_args["job-payload-json"] == '{"executable": "/bin/bash", "arguments": ["-lc", "echo hello"]}'
    assert argparse_args["headers-json"] == '{"X-Client": "clearml-iri-bridge"}'
    fake_task.set_parameters_as_dict.assert_called_once()
    fake_task.set_tags.assert_called_once_with(["iri-bridge"])
