# Developing

## Setup

Set up a development environment with [uv](https://docs.astral.sh/uv/):

```console
$ make setup-venv
```

Common tasks (run `make help` for the full list):

```console
$ make lint      # isort, ruff, flake8, black, mypy
$ make format    # auto-format with isort and black
$ make test      # run the test suite
$ make docs      # build the Sphinx HTML docs
```

## Releasing

`gxy-wes-bioblend` publishes to PyPI via GitHub Actions
[trusted publishing](https://docs.pypi.org/trusted-publishers/) — no PyPI
tokens or `~/.pypirc` are needed on any machine. Pushing a version tag to
`jmchilton/gxy-wes-bioblend` triggers the `deploy.yaml` workflow, which builds
the sdist and wheel and uploads them to PyPI over OIDC.

### One-time PyPI setup

Before the first release, register the workflow as a trusted publisher. Since
the project does not exist on PyPI yet, add a *pending* publisher at
<https://pypi.org/manage/account/publishing/>:

| Field           | Value               |
| --------------- | ------------------- |
| PyPI Project    | `gxy-wes-bioblend`  |
| Owner           | `jmchilton`         |
| Repository name | `gxy-wes-bioblend`  |
| Workflow name   | `deploy.yaml`       |
| Environment     | *(leave blank)*     |

After the first successful publish this becomes a normal trusted publisher and
needs no further attention.

### Cutting a release

1. Set the release version in `gxy_wes_bioblend/__init__.py` — drop the `.devN`
   suffix from `__version__` (e.g. `0.1.0.dev0` → `0.1.0`). The package version
   is read from this attribute.

2. Sanity-check the build locally:

   ```console
   $ make dist
   ```

   This builds the sdist and wheel and runs `twine check` on them.

3. Commit the version bump, tag the release, and push the tag:

   ```console
   $ git commit -am "Release 0.1.0"
   $ git tag v0.1.0
   $ git push origin main v0.1.0
   ```

   The pushed tag triggers the publish workflow. The `pypi-publish` job only
   runs for tag pushes on `jmchilton/gxy-wes-bioblend`, so tags on forks are
   safe.

4. Bump `__version__` to the next development version (e.g. `0.2.0.dev0`) and
   commit so `main` is ready for ongoing work.
