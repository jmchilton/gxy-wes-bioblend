# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute command (flake8, sphinx, twine, etc...)
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
SOURCE_DIR?=gxy_wes_bioblend
TEST_DIR?=tests
DOCS_DIR?=docs
PROJECT_NAME?=gxy-wes-bioblend
PROJECT_URL?=https://github.com/jmchilton/$(PROJECT_NAME)

.PHONY: clean clean-build clean-pyc clean-test setup-venv lint format mypy test coverage docs open-docs dist help

help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/ dist/ *.egg-info

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/ .coverage htmlcov/

setup-venv: ## setup a development virtualenv with uv (falls back to pip)
	if command -v uv > /dev/null 2>&1; then \
		uv sync; \
	else \
		if [ ! -d $(VENV) ]; then python3 -m venv $(VENV); fi; \
		$(IN_VENV) pip install -e . && pip install -r dev-requirements.txt; \
	fi

lint: ## check style with isort, ruff, flake8, black, and mypy
	uv run --group lint isort --check --diff .
	uv run --group lint ruff check
	uv run --group lint flake8
	uv run --group lint black --check --diff .
	uv run --group mypy mypy $(SOURCE_DIR)

format: ## auto-format with isort and black
	uv run --group lint isort .
	uv run --group lint black .

mypy: ## check type annotations
	uv run --group mypy mypy $(SOURCE_DIR)

test: ## run tests with the default Python
	uv run --group test pytest $(TEST_DIR)

coverage: ## check code coverage
	uv run --group test coverage run --source $(SOURCE_DIR) -m pytest $(TEST_DIR)
	uv run --group test coverage report -m
	uv run --group test coverage html

docs: ## generate Sphinx HTML documentation
	uv run --group docs $(MAKE) -C $(DOCS_DIR) clean
	uv run --group docs $(MAKE) -C $(DOCS_DIR) html

open-docs: docs ## generate docs and open in browser
	open $(DOCS_DIR)/_build/html/index.html || xdg-open $(DOCS_DIR)/_build/html/index.html

dist: clean ## build sdist and wheel
	uv run --group build python -m build
	uv run --group build twine check dist/*
	ls -l dist
