# gxy-wes-bioblend

A client and command line tool for [Galaxy](https://galaxyproject.org)'s
[GA4GH Workflow Execution Service (WES)](https://ga4gh.github.io/workflow-execution-service-schemas/)
API, built on the [BioBlend](https://bioblend.readthedocs.io/) client layer.

It is the BioBlend-based sibling of
[gxy-wes](https://github.com/jmchilton/gxy-wes). Both walk the same flow —
discover the service, stage an input dataset, submit a workflow, poll the run,
read outputs and per-task logs — but where `gxy-wes` uses a hand-rolled
`requests` wrapper to stay dependency-light, this project layers the WES
endpoints on top of BioBlend's `GalaxyInstance`.

## Why BioBlend

BioBlend does not implement the WES endpoints, but it already provides
everything around them, so there is no reason to re-write it:

- **API-key storage and auth headers** — `GalaxyInstance` holds the key and
  attaches `x-api-key` (or a bearer token) to every request.
- **Request and retry plumbing** — the `Client` base's `_get`/`_post` handle
  JSON decoding, multipart encoding, retries, and consistent `ConnectionError`s.
- **Upload and staging** — `gi.tools.paste_content` / `gi.tools.upload_file`
  and `gi.histories` create the input datasets WES expects to already exist.
- **Job logs** — `gi.jobs.show_job(..., full_details=True)` exposes
  stdout/stderr without a bespoke endpoint call.

`WesClient` adds only the WES wire protocol, as an ordinary
`bioblend.galaxy.client.Client` subclass — except its endpoints are rooted at
`<galaxy>/ga4gh/wes/v1` instead of `<galaxy>/api`.

## Scope

This project exists to **demonstrate the WES API the BioBlend way** — the shape
a production application would use. For comparison:

- For the minimal, dependency-light demonstration, see
  [gxy-wes](https://github.com/jmchilton/gxy-wes).
- For user-facing applications, use [Planemo](https://planemo.readthedocs.io/).

## Install

Run it without installing using [uv](https://docs.astral.sh/uv/):

```console
$ uvx gxy-wes-bioblend service-info --galaxy-url http://localhost:8080
```

Or install it:

```console
$ pip install gxy-wes-bioblend
```

## Authentication

Authentication is handled by BioBlend's `GalaxyInstance`. Every endpoint except
`service-info` needs a Galaxy API key. Pass `--api-key` or set
`GXY_WES_API_KEY`; set the server with `--galaxy-url` or `GXY_WES_URL`. Get a
key with:

```console
$ curl -s -u you@example.com:password \
    http://localhost:8080/api/authenticate/baseauth
```

## Usage

Each WES endpoint is a subcommand:

```console
$ gxy-wes-bioblend service-info
$ gxy-wes-bioblend stage --content $'hello\nworld\n'   # -> {history_id, hda_id}
$ gxy-wes-bioblend submit --workflow simple.gxwf.yml \
    --params '{"input1": {"src": "hda", "id": "<hda_id>"}}' \
    --engine-parameters '{"history_id": "<history_id>"}'
$ gxy-wes-bioblend status <run_id>
$ gxy-wes-bioblend get <run_id>
$ gxy-wes-bioblend tasks <run_id>
$ gxy-wes-bioblend task <run_id> 1
$ gxy-wes-bioblend list
$ gxy-wes-bioblend cancel <run_id>
$ gxy-wes-bioblend job-output <job_id> --which stderr
```

The `demo` subcommand runs the whole example end to end against a live Galaxy
(stage an input, submit the bundled Format2 workflow, poll, print outputs and
tasks):

```console
$ export GXY_WES_API_KEY=...
$ uvx gxy-wes-bioblend demo --galaxy-url http://localhost:8080
```

## As a library

Construct a `WesClient` from a BioBlend `GalaxyInstance`, just like any other
BioBlend client:

```python
from bioblend.galaxy import GalaxyInstance
from gxy_wes_bioblend import WesClient

gi = GalaxyInstance("http://localhost:8080", key="...")
wes = WesClient(gi)

info = wes.service_info()
staged = wes.stage_paste("hello\nworld\n")          # uses gi.histories + gi.tools
run = wes.submit_run(
    workflow_type="gx_workflow_format2",
    workflow_path="simple.gxwf.yml",
    params={"input1": {"src": "hda", "id": staged["hda_id"]}},
    engine_parameters={"history_id": staged["history_id"]},
)
status = wes.get_run_status(run["run_id"])
```

A `connect()` convenience constructor builds the `GalaxyInstance` for you:

```python
from gxy_wes_bioblend import connect

wes = connect("http://localhost:8080", api_key="...")
```

## Notes

- `workflow_type` is one of Galaxy's formats: `gx_workflow_format2` (Format2
  YAML) or `gx_workflow_ga` (native `.ga` JSON). It is detected from the workflow
  content when you pass `--workflow`.
- WES has no data-staging endpoint; dataset inputs must already exist in Galaxy
  and are referenced as `{"src": "hda", "id": ...}`. The `stage` subcommand uses
  BioBlend's tools client to create those.
- WES errors surface as BioBlend's `ConnectionError` (re-exported here as
  `WesError`), which carries `status_code` and a `body` attribute.
- Run success is determined by the WES run `state` (`COMPLETE`), not by per-task
  exit codes — a failed job can be a normal part of a valid workflow.

## License

MIT. See [LICENSE](https://github.com/jmchilton/gxy-wes-bioblend/blob/main/LICENSE).
