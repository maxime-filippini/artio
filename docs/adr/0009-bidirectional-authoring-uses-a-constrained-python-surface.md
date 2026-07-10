# Bidirectional authoring uses a constrained Python surface

Artio treats Python/Polars Workflow definitions as canonical and reparses file changes to synchronize its graph, decision trees, diagnostics, and Preview. Its initial controlled, Marimo-style serialization boundary comprises managed decorators, source/output declarations, common `LazyFrame` transformations, and `when`/`then`/`otherwise` expressions; unsupported dynamic code remains visible as an opaque code-backed Transformation instead of being rewritten or discarded.
