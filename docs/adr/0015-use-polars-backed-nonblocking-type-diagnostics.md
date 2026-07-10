# Use Polars-backed nonblocking type diagnostics

Artio asks Polars to resolve a LazyFrame schema and displays resolved, unresolved, or failing type information as a Diagnostic; it does not implement its own branch-type system or block source edits that it cannot prove safe. Bounded Preview execution remains the final check for runtime and data-dependent behavior.
