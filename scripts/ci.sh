#!/usr/bin/env bash

set -euo pipefail

uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
