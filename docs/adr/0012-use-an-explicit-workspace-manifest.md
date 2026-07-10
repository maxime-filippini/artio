# Use an explicit workspace manifest

`artio open <workspace>` reads `artio.toml` to identify the Workflow definition files and local Parquet Sample data bindings it may manage. Artio does not scan arbitrary Python files, which keeps parsing and Preview execution within an explicit workspace boundary.
