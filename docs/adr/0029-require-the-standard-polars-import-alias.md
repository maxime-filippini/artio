# Require the standard Polars import alias

Managed Artio modules initially import Polars as `import polars as pl`. The parser and source rewriter recognize this fixed alias and do not attempt to resolve arbitrary aliases, indirect imports, or re-exports until the core bidirectional format is stable.
