"""Unit tests for the BioBlend-backed WES client and CLI parser.

HTTP is mocked with ``responses``; BioBlend still issues real ``requests``
calls, so the mocks exercise the same plumbing the library uses in production.
"""

import pytest
import responses

from gxy_wes_bioblend import (
    connect,
    detect_workflow_type,
    WesClient,
    WesError,
)
from gxy_wes_bioblend.cli import (
    _parser,
    example_workflow_text,
)

BASE = "http://galaxy.example"


def _client(api_key="secret"):
    return connect(BASE, api_key=api_key)


def test_detect_workflow_type_format2():
    assert detect_workflow_type("class: GalaxyWorkflow\nsteps: {}\n") == "gx_workflow_format2"


def test_detect_workflow_type_native_json():
    assert detect_workflow_type('{"steps": {}, "a_galaxy_workflow": "true"}') == "gx_workflow_ga"


def test_detect_workflow_type_format2_json():
    assert detect_workflow_type('{"class": "GalaxyWorkflow"}') == "gx_workflow_format2"


def test_example_workflow_bundled():
    assert "class: GalaxyWorkflow" in example_workflow_text()


def test_connect_returns_wes_client_on_galaxy_instance():
    client = _client()
    assert isinstance(client, WesClient)
    # The WES client is layered on a BioBlend GalaxyInstance that stores the key.
    assert client.gi.key == "secret"
    assert client.gi.base_url == BASE


def test_parser_builds_and_requires_command():
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    # Connection options must work *after* the subcommand (natural CLI usage).
    args = parser.parse_args(["status", "abc123", "--galaxy-url", BASE, "--api-key", "k"])
    assert args.command == "status"
    assert args.run_id == "abc123"
    assert args.galaxy_url == BASE
    assert args.api_key == "k"


@responses.activate
def test_service_info():
    responses.add(
        responses.GET,
        f"{BASE}/ga4gh/wes/v1/service-info",
        json={"name": "Galaxy WES API"},
        status=200,
    )
    assert _client().service_info()["name"] == "Galaxy WES API"


@responses.activate
def test_submit_run_sends_multipart_and_params():
    responses.add(
        responses.POST,
        f"{BASE}/ga4gh/wes/v1/runs",
        json={"run_id": "r1"},
        status=200,
    )
    result = _client().submit_run(
        workflow_type="gx_workflow_format2",
        workflow_url="gxworkflow://abc",
        params={"input1": {"src": "hda", "id": "x"}},
        engine_parameters={"history_id": "h1"},
    )
    assert result["run_id"] == "r1"
    request = responses.calls[0].request
    # BioBlend's GalaxyInstance attaches the key on every request.
    assert request.headers["x-api-key"] == "secret"
    # WES /runs is always multipart/form-data (BioBlend MultipartEncoder).
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    body = request.body
    if not isinstance(body, bytes):
        body = body.to_string()  # MultipartEncoder
    text = body.decode()
    assert "gx_workflow_format2" in text
    assert "gxworkflow://abc" in text


@responses.activate
def test_cancel_run_posts():
    responses.add(
        responses.POST,
        f"{BASE}/ga4gh/wes/v1/runs/r1/cancel",
        json={"run_id": "r1"},
        status=200,
    )
    assert _client().cancel_run("r1") == {"run_id": "r1"}
    assert responses.calls[0].request.method == "POST"


@responses.activate
def test_list_runs_sends_pagination_params():
    responses.add(responses.GET, f"{BASE}/ga4gh/wes/v1/runs", json={"runs": []}, status=200)
    _client().list_runs(page_size=3, page_token="tok")
    url = responses.calls[0].request.url
    assert "page_size=3" in url
    assert "page_token=tok" in url


@responses.activate
def test_get_run_task_hits_nested_url():
    responses.add(
        responses.GET,
        f"{BASE}/ga4gh/wes/v1/runs/r1/tasks/2",
        json={"id": "2"},
        status=200,
    )
    assert _client().get_run_task("r1", "2")["id"] == "2"


@responses.activate
def test_error_body_surfaces_via_connection_error():
    responses.add(
        responses.GET,
        f"{BASE}/ga4gh/wes/v1/runs/missing",
        json={"err_msg": "Invocation missing not found", "err_code": 0},
        status=404,
    )
    with pytest.raises(WesError) as excinfo:
        _client().get_run("missing")
    assert excinfo.value.status_code == 404
    assert "Invocation missing not found" in str(excinfo.value)


@responses.activate
def test_job_output_via_jobs_client():
    responses.add(
        responses.GET,
        f"{BASE}/api/jobs/j1",
        json={"tool_stderr": "boom\n", "tool_stdout": ""},
        status=200,
    )
    assert _client().job_output("j1", which="stderr") == "boom\n"


@responses.activate
def test_stage_paste_uses_histories_and_tools_clients():
    responses.add(responses.POST, f"{BASE}/api/histories", json={"id": "h1"}, status=200)
    responses.add(
        responses.POST,
        f"{BASE}/api/tools",
        json={"outputs": [{"id": "hda1"}], "jobs": [{"id": "job1"}]},
        status=200,
    )
    staged = _client().stage_paste("the content", name="thing", ext="txt")
    assert staged == {"history_id": "h1", "hda_id": "hda1"}
    # The paste went through BioBlend's tools client (POST /api/tools) and
    # carried the actual content + dataset name -- not just an empty url_paste.
    paste_body = responses.calls[1].request.body
    if isinstance(paste_body, bytes):
        paste_body = paste_body.decode()
    assert "url_paste" in paste_body
    assert "the content" in paste_body
    assert "thing" in paste_body
