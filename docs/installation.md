# Installation

`gxy-wes-bioblend` depends on [BioBlend](https://bioblend.readthedocs.io/)
(which in turn pulls in `requests`). The easiest way to use it is with
[uv](https://docs.astral.sh/uv/) — no install step:

```console
$ uvx gxy-wes-bioblend service-info --galaxy-url http://localhost:8080
```

To install it into an environment instead:

```console
$ pip install gxy-wes-bioblend
```

Or, for development from a checkout:

```console
$ make setup-venv   # uv sync
```

## Authentication

Authentication is handled by BioBlend's `GalaxyInstance`. Every endpoint except
`service-info` requires a Galaxy API key; provide it with `--api-key` or the
`GXY_WES_API_KEY` environment variable, and point at your server with
`--galaxy-url` or `GXY_WES_URL`.

Mint a key for an existing account with HTTP basic auth:

```console
$ curl -s -u you@example.com:password \
    http://localhost:8080/api/authenticate/baseauth
{"api_key": "..."}
```
