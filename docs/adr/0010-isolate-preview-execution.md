# Isolate preview execution

Each Preview runs user- or agent-authored workflow code in a separate local worker process with time and memory limits, exposing only the declared local Parquet Sample data. FastAPI does not execute preview code in-process, and Artio does not rely on an in-process Python sandbox as its safety boundary.
