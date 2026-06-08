# Usage

Each Galaxy WES endpoint maps to a subcommand. The flow below mirrors the Galaxy
developer docs: discover the service, stage an input, submit a workflow, poll,
then read outputs and per-task logs. Every call is routed through a BioBlend
`GalaxyInstance`.

```console
$ export GXY_WES_URL=http://localhost:8080
$ export GXY_WES_API_KEY=...
```

## Discover the service

```console
$ gxy-wes-bioblend service-info
```

## Stage an input dataset

WES has no upload endpoint, so dataset inputs must already exist in Galaxy. The
`stage` subcommand reuses BioBlend's histories and tools clients to create a
history and upload a dataset, printing the ids you then reference:

```console
$ gxy-wes-bioblend stage --content $'line one\nline two\n'
{
  "hda_id": "1e8ab44153008be8",
  "history_id": "e85a3be143d5905b"
}
```

## Submit a run

```console
$ gxy-wes-bioblend submit \
    --workflow simple.gxwf.yml \
    --params '{"input1": {"src": "hda", "id": "1e8ab44153008be8"}}' \
    --engine-parameters '{"history_id": "e85a3be143d5905b"}'
{"run_id": "33b43b4e7093c91f"}
```

`workflow_type` is detected from the workflow content (`gx_workflow_format2` for
Format2 YAML, `gx_workflow_ga` for native `.ga`); override with `--workflow-type`.

## Monitor and read results

```console
$ gxy-wes-bioblend status 33b43b4e7093c91f
$ gxy-wes-bioblend get 33b43b4e7093c91f       # full run log + outputs (with DRS URIs)
$ gxy-wes-bioblend tasks 33b43b4e7093c91f
$ gxy-wes-bioblend task 33b43b4e7093c91f 1
$ gxy-wes-bioblend job-output <job_id> --which stderr
```

Run success is determined by the WES run `state` reaching `COMPLETE`, not by
per-task exit codes — a failed job can be a normal part of a valid workflow.

## The whole example at once

```console
$ gxy-wes-bioblend demo
```

`demo` stages an input, submits the bundled Format2 workflow, polls until the run
is terminal, and prints the outputs and tasks.
