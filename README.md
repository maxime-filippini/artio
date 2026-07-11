# Artio

## Development

Install the development environment and run the project checks with uv:

```sh
./scripts/ci.sh
```

The script runs the same dependency sync, formatting, lint, type, and test
commands as GitHub Actions. To run an individual check, use its corresponding
`uv run` command directly.

Ruff and ty read their shared project configuration from `pyproject.toml`.
Install their editor extensions locally; they will use the same configuration.
