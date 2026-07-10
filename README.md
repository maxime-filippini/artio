# Artio

## Development

Install the development environment and run the project checks with uv:

```sh
uv sync
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

Ruff and ty read their shared project configuration from `pyproject.toml`.
Install their editor extensions locally; they will use the same configuration.
