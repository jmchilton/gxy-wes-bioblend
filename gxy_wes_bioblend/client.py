"""A Galaxy GA4GH WES client built on the BioBlend client layer.

Where the sibling ``gxy-wes`` project talks to Galaxy through a hand-rolled
:mod:`requests` wrapper, this client reuses BioBlend's
:class:`~bioblend.galaxy.GalaxyInstance` for everything that is *not*
WES-specific: API-key storage and auth headers, the request/retry plumbing
(:meth:`~bioblend.galaxy.client.Client._get` / ``_post``), dataset upload
(:mod:`bioblend.galaxy.tools`), history creation, dataset state, and job log
retrieval.

Only the WES wire protocol -- which BioBlend does not implement -- is added
here. :class:`WesClient` is an ordinary :class:`bioblend.galaxy.client.Client`
subclass, except its endpoints are rooted at ``<galaxy>/ga4gh/wes/v1`` rather
than the usual ``<galaxy>/api`` module path.
"""

import json
from typing import (
    Any,
    Optional,
)

from bioblend import ConnectionError as BioblendConnectionError
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.client import Client
from bioblend.util import attach_file

WES_PREFIX = "ga4gh/wes/v1"

# WES run states that mean "stop polling".
TERMINAL_STATES = frozenset({"COMPLETE", "EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED"})
# Terminal states that indicate the run did not succeed.
FAILURE_STATES = frozenset({"EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED"})
# Galaxy dataset states that mean a staged input has settled.
DATASET_TERMINAL_STATES = frozenset({"ok", "error", "discarded"})

# WES calls surface BioBlend's ConnectionError (it carries ``status_code`` and a
# ``body`` attribute). Re-exported under a WES-friendly name.
WesError = BioblendConnectionError


def detect_workflow_type(workflow_text: str) -> str:
    """Guess the Galaxy WES ``workflow_type`` from a workflow document.

    Returns ``gx_workflow_format2`` for Format2 (``class: GalaxyWorkflow``) or
    ``gx_workflow_ga`` for native ``.ga`` workflows. Galaxy re-validates the type
    against the uploaded content, so this only needs to be approximately right.
    """
    text = workflow_text.lstrip()
    if text.startswith("{"):
        try:
            parsed = json.loads(workflow_text)
        except ValueError:
            parsed = {}
        if isinstance(parsed, dict) and parsed.get("class") == "GalaxyWorkflow":
            return "gx_workflow_format2"
        return "gx_workflow_ga"
    # YAML-ish: Format2 documents declare ``class: GalaxyWorkflow``.
    if "class: GalaxyWorkflow" in workflow_text or "class: 'GalaxyWorkflow'" in workflow_text:
        return "gx_workflow_format2"
    return "gx_workflow_ga"


def connect(galaxy_url: str, api_key: Optional[str] = None, **kwargs: Any) -> "WesClient":
    """Build a :class:`WesClient` backed by a fresh BioBlend ``GalaxyInstance``.

    Extra keyword arguments are forwarded to
    :class:`~bioblend.galaxy.GalaxyInstance` (e.g. ``email``/``password``,
    ``token``, ``verify``).
    """
    gi = GalaxyInstance(url=galaxy_url, key=api_key, **kwargs)
    return WesClient(gi)


class WesClient(Client):
    """Galaxy GA4GH WES client layered on a BioBlend ``GalaxyInstance``.

    Construct it from a ``GalaxyInstance`` like any other BioBlend client::

        from bioblend.galaxy import GalaxyInstance
        from gxy_wes_bioblend import WesClient

        gi = GalaxyInstance("http://localhost:8080", key="...")
        wes = WesClient(gi)
        wes.service_info()

    or via the :func:`connect` convenience constructor.
    """

    # Required by the Client base; WES is not under /api, so it is not actually
    # used for URL composition -- see :meth:`_wes_url`.
    module = WES_PREFIX

    def __init__(self, galaxy_instance: GalaxyInstance) -> None:
        super().__init__(galaxy_instance)
        # Narrow the type so the BioBlend sub-clients (tools, histories, jobs,
        # datasets) used below are visible to type checkers.
        self.gi: GalaxyInstance = galaxy_instance

    # -- URL helper --------------------------------------------------------

    def _wes_url(self, path: str = "") -> str:
        """Compose a WES URL under ``<base_url>/ga4gh/wes/v1`` (not ``/api``)."""
        root = "/".join((self.gi.base_url, WES_PREFIX))
        return f"{root}/{path.lstrip('/')}" if path else root

    # -- WES wire protocol -------------------------------------------------

    def service_info(self) -> dict[str, Any]:
        return self._get(url=self._wes_url("service-info"))

    def submit_run(
        self,
        *,
        workflow_type: str,
        workflow_type_version: str = "1.0.0",
        workflow_path: Optional[str] = None,
        workflow_url: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        engine_parameters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Submit a workflow run, returning ``{"run_id": ...}``.

        WES ``/runs`` only accepts ``multipart/form-data``, so the request is
        always sent multipart (BioBlend's ``files_attached=True`` path), with the
        workflow document attached via :func:`bioblend.util.attach_file`.
        """
        if not workflow_path and not workflow_url:
            raise ValueError("Provide either workflow_path or workflow_url")

        payload: dict[str, Any] = {
            "workflow_type": workflow_type,
            "workflow_type_version": workflow_type_version,
        }
        if params is not None:
            payload["workflow_params"] = json.dumps(params)
        if engine_parameters is not None:
            payload["workflow_engine_parameters"] = json.dumps(engine_parameters)
        if workflow_url is not None:
            payload["workflow_url"] = workflow_url

        attachment = attach_file(workflow_path) if workflow_path else None
        if attachment is not None:
            payload["workflow_attachment"] = attachment
        try:
            return self._post(payload, url=self._wes_url("runs"), files_attached=True)
        finally:
            if attachment is not None:
                attachment.close()

    def list_runs(self, page_size: int = 10, page_token: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        return self._get(url=self._wes_url("runs"), params=params)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._get(url=self._wes_url(f"runs/{run_id}"))

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        return self._get(url=self._wes_url(f"runs/{run_id}/status"))

    def cancel_run(self, run_id: str) -> dict[str, Any]:
        return self._post(url=self._wes_url(f"runs/{run_id}/cancel"))

    def get_run_tasks(self, run_id: str, page_size: int = 10, page_token: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        return self._get(url=self._wes_url(f"runs/{run_id}/tasks"), params=params)

    def get_run_task(self, run_id: str, task_id: str) -> dict[str, Any]:
        return self._get(url=self._wes_url(f"runs/{run_id}/tasks/{task_id}"))

    # -- staging + logs via BioBlend's native clients ----------------------
    #
    # WES has no data-staging endpoint of its own, so inputs must already exist
    # in Galaxy. Rather than hand-roll /api/tools/fetch and /api/jobs calls (as
    # the sibling gxy-wes does), reuse BioBlend's tools/histories/jobs clients.

    def stage_paste(
        self,
        content: str,
        *,
        history_name: str = "WES Demo",
        name: str = "wes_input",
        ext: str = "txt",
    ) -> dict[str, str]:
        """Create a history and upload pasted text as a dataset.

        Returns ``{"history_id": ..., "hda_id": ...}`` -- the ids you reference
        from ``submit_run`` as ``{"src": "hda", "id": hda_id}`` and
        ``{"history_id": history_id}``.
        """
        history = self.gi.histories.create_history(name=history_name)
        result = self.gi.tools.paste_content(content, history["id"], file_type=ext, file_name=name)
        hda = result["outputs"][0]
        return {"history_id": history["id"], "hda_id": hda["id"]}

    def dataset_state(self, hda_id: str, history_id: Optional[str] = None) -> str:
        """Return a dataset's Galaxy state (e.g. ``ok``, ``running``, ``error``)."""
        if history_id is not None:
            body = self.gi.histories.show_dataset(history_id, hda_id)
        else:
            body = self.gi.datasets.show_dataset(hda_id)
        return body.get("state", "unknown")

    def job_output(self, job_id: str, which: str = "stdout") -> str:
        """Fetch a job's ``stdout`` or ``stderr`` via BioBlend's jobs client."""
        if which not in ("stdout", "stderr"):
            raise ValueError("which must be 'stdout' or 'stderr'")
        details = self.gi.jobs.show_job(job_id, full_details=True)
        return details.get(f"tool_{which}", "")
