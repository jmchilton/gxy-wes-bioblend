"""gxy-wes-bioblend command line interface.

A subcommand-per-endpoint walkthrough of Galaxy's GA4GH WES API, plus a "demo"
subcommand that runs the whole example end to end -- the same surface as the
sibling ``gxy-wes`` CLI, but every call is routed through a BioBlend
``GalaxyInstance``.
"""

import argparse
import json
import os
import sys
import time
from typing import (
    Any,
    Optional,
)

try:
    from importlib.resources import files as _resource_files
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    _resource_files = None  # type: ignore[assignment]

from . import __version__
from .client import (
    connect,
    DATASET_TERMINAL_STATES,
    detect_workflow_type,
    FAILURE_STATES,
    TERMINAL_STATES,
    WesClient,
    WesError,
)

ENV_URL = "GXY_WES_URL"
ENV_KEY = "GXY_WES_API_KEY"


def _emit(value: Any) -> None:
    """Pretty-print a JSON-serializable value (or raw text) to stdout."""
    if isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def _client(args: argparse.Namespace) -> WesClient:
    return connect(args.galaxy_url, api_key=args.api_key)


def example_workflow_text() -> str:
    """Return the bundled minimal Format2 workflow as text."""
    if _resource_files is not None:
        return (_resource_files("gxy_wes_bioblend.examples") / "simple.gxwf.yml").read_text(encoding="utf-8")
    raise RuntimeError("Bundled examples require Python 3.9+ importlib.resources")  # pragma: no cover


# -- subcommand handlers ---------------------------------------------------


def _cmd_service_info(args: argparse.Namespace) -> int:
    _emit(_client(args).service_info())
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    client = _client(args)
    params = json.loads(args.params) if args.params else None
    engine_parameters = json.loads(args.engine_parameters) if args.engine_parameters else None
    workflow_type = args.workflow_type
    if workflow_type is None and args.workflow:
        with open(args.workflow, encoding="utf-8") as handle:
            workflow_type = detect_workflow_type(handle.read())
    _emit(
        client.submit_run(
            workflow_type=workflow_type or "gx_workflow_format2",
            workflow_type_version=args.workflow_type_version,
            workflow_path=args.workflow,
            workflow_url=args.workflow_url,
            params=params,
            engine_parameters=engine_parameters,
        )
    )
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    _emit(_client(args).get_run_status(args.run_id))
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    _emit(_client(args).get_run(args.run_id))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    _emit(_client(args).list_runs(page_size=args.page_size, page_token=args.page_token))
    return 0


def _cmd_cancel(args: argparse.Namespace) -> int:
    _emit(_client(args).cancel_run(args.run_id))
    return 0


def _cmd_tasks(args: argparse.Namespace) -> int:
    _emit(_client(args).get_run_tasks(args.run_id, page_size=args.page_size, page_token=args.page_token))
    return 0


def _cmd_task(args: argparse.Namespace) -> int:
    _emit(_client(args).get_run_task(args.run_id, args.task_id))
    return 0


def _cmd_job_output(args: argparse.Namespace) -> int:
    _emit(_client(args).job_output(args.job_id, which=args.which))
    return 0


def _cmd_stage(args: argparse.Namespace) -> int:
    client = _client(args)
    staged = client.stage_paste(args.content, history_name=args.history_name, name=args.name, ext=args.ext)
    _emit(staged)
    return 0


def _wait_for_dataset(client: WesClient, history_id: str, hda_id: str, attempts: int, interval: float) -> str:
    state = "new"
    for _ in range(attempts):
        state = client.dataset_state(hda_id, history_id=history_id)
        if state in DATASET_TERMINAL_STATES:
            return state
        time.sleep(interval)
    return state


def _poll_run(client: WesClient, run_id: str, attempts: int, interval: float) -> str:
    state = "UNKNOWN"
    for _ in range(attempts):
        state = client.get_run_status(run_id).get("state", "UNKNOWN")
        if state in TERMINAL_STATES:
            return state
        time.sleep(interval)
    return state


def _cmd_demo(args: argparse.Namespace) -> int:
    """Walk the whole example: stage -> submit -> poll -> outputs -> tasks."""
    if not args.api_key:
        print(f"error: demo needs an API key (--api-key or ${ENV_KEY})", file=sys.stderr)
        return 2

    client = _client(args)

    print("==> service-info")
    info = client.service_info()
    print(f"    {info.get('name')} {info.get('version')}; types: {list(info.get('workflow_type_versions', {}))}")

    print("==> staging an input dataset")
    staged = client.stage_paste("line one\nline two\nline three\n", history_name="gxy-wes-bioblend demo")
    history_id, hda_id = staged["history_id"], staged["hda_id"]
    state = _wait_for_dataset(client, history_id, hda_id, args.attempts, args.interval)
    print(f"    history={history_id} hda={hda_id} state={state}")
    if state != "ok":
        print(f"error: input dataset did not become ok (state={state})", file=sys.stderr)
        return 1

    print("==> writing the bundled Format2 workflow and submitting")
    workflow_text = example_workflow_text()
    workflow_type = detect_workflow_type(workflow_text)
    workflow_path = os.path.join(args.workdir or ".", "gxy-wes-bioblend-demo.gxwf.yml")
    with open(workflow_path, "w", encoding="utf-8") as handle:
        handle.write(workflow_text)
    submitted = client.submit_run(
        workflow_type=workflow_type,
        workflow_path=workflow_path,
        params={"input1": {"src": "hda", "id": hda_id}},
        engine_parameters={"history_id": history_id},
    )
    run_id = submitted["run_id"]
    print(f"    run_id={run_id} (workflow_type={workflow_type})")

    print("==> polling status")
    final_state = _poll_run(client, run_id, args.attempts, args.interval)
    print(f"    state={final_state}")

    print("==> run log + outputs")
    run_log = client.get_run(run_id)
    _emit(run_log.get("outputs"))

    print("==> tasks")
    tasks = client.get_run_tasks(run_id).get("task_logs") or []
    for task in tasks:
        print(f"    task {task.get('id')}: {task.get('name')} exit_code={task.get('exit_code')}")

    if final_state in FAILURE_STATES:
        print(f"error: run finished in failure state {final_state}", file=sys.stderr)
        return 1
    print("==> done")
    return 0


# -- parser ----------------------------------------------------------------


def _common_parser() -> argparse.ArgumentParser:
    """Parent parser of connection options shared by every subcommand.

    Added to each subparser via ``parents=`` so the options may follow the
    subcommand (e.g. ``gxy-wes-bioblend demo --galaxy-url ...``).
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--galaxy-url",
        default=os.environ.get(ENV_URL, "http://localhost:8080"),
        help=f"Galaxy base URL (env {ENV_URL}; default http://localhost:8080).",
    )
    common.add_argument(
        "--api-key",
        default=os.environ.get(ENV_KEY),
        help=f"Galaxy API key (env {ENV_KEY}).",
    )
    return common


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser (also used by sphinx-argparse)."""
    parser = argparse.ArgumentParser(prog="gxy-wes-bioblend", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = _common_parser()
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    p_info = subparsers.add_parser("service-info", help="GET service-info (public).", parents=[common])
    p_info.set_defaults(func=_cmd_service_info)

    p_stage = subparsers.add_parser("stage", help="Create a history and upload an input dataset.", parents=[common])
    p_stage.add_argument("--content", default="line one\nline two\nline three\n", help="Dataset content to paste.")
    p_stage.add_argument("--name", default="wes_input", help="Dataset name.")
    p_stage.add_argument("--ext", default="txt", help="Galaxy datatype extension.")
    p_stage.add_argument("--history-name", default="WES Demo", help="History name.")
    p_stage.set_defaults(func=_cmd_stage)

    p_submit = subparsers.add_parser("submit", help="POST a workflow run.", parents=[common])
    p_submit.add_argument("--workflow", help="Path to a Galaxy workflow file (Format2 YAML or native .ga).")
    p_submit.add_argument("--workflow-url", help="A workflow URL or gxworkflow:// reference instead of a file.")
    p_submit.add_argument(
        "--workflow-type",
        choices=["gx_workflow_format2", "gx_workflow_ga"],
        help="Override the workflow type (otherwise detected from --workflow content).",
    )
    p_submit.add_argument("--workflow-type-version", default="1.0.0", help="workflow_type_version field.")
    p_submit.add_argument("--params", help="workflow_params as a JSON string.")
    p_submit.add_argument("--engine-parameters", help="workflow_engine_parameters as a JSON string.")
    p_submit.set_defaults(func=_cmd_submit)

    p_status = subparsers.add_parser("status", help="GET run status.", parents=[common])
    p_status.add_argument("run_id")
    p_status.set_defaults(func=_cmd_status)

    p_get = subparsers.add_parser("get", help="GET the full run log.", parents=[common])
    p_get.add_argument("run_id")
    p_get.set_defaults(func=_cmd_get)

    p_list = subparsers.add_parser("list", help="List the user's runs.", parents=[common])
    p_list.add_argument("--page-size", type=int, default=10)
    p_list.add_argument("--page-token")
    p_list.set_defaults(func=_cmd_list)

    p_cancel = subparsers.add_parser("cancel", help="Cancel a run.", parents=[common])
    p_cancel.add_argument("run_id")
    p_cancel.set_defaults(func=_cmd_cancel)

    p_tasks = subparsers.add_parser("tasks", help="List a run's tasks.", parents=[common])
    p_tasks.add_argument("run_id")
    p_tasks.add_argument("--page-size", type=int, default=10)
    p_tasks.add_argument("--page-token")
    p_tasks.set_defaults(func=_cmd_tasks)

    p_task = subparsers.add_parser("task", help="Get one task by id (e.g. 0, 1.2).", parents=[common])
    p_task.add_argument("run_id")
    p_task.add_argument("task_id")
    p_task.set_defaults(func=_cmd_task)

    p_job = subparsers.add_parser("job-output", help="Fetch a job's stdout/stderr.", parents=[common])
    p_job.add_argument("job_id")
    p_job.add_argument("--which", choices=["stdout", "stderr"], default="stdout")
    p_job.set_defaults(func=_cmd_job_output)

    p_demo = subparsers.add_parser("demo", help="Run the whole example end to end.", parents=[common])
    p_demo.add_argument("--attempts", type=int, default=60, help="Max poll attempts for dataset/run.")
    p_demo.add_argument("--interval", type=float, default=2.0, help="Seconds between polls.")
    p_demo.add_argument("--workdir", help="Directory to write the demo workflow file (default: cwd).")
    p_demo.set_defaults(func=_cmd_demo)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except WesError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
