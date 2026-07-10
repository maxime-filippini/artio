# Use the workspace Python environment for previews

By default, Artio runs Preview workers with the Python interpreter that launched `artio open`, with an explicit interpreter override available in `artio.toml`. Artio does not create or manage virtual environments in the first release, keeping execution aligned with the workspace's Polars and project dependencies.
