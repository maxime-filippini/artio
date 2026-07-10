# Bidirectional authoring uses declarative registration and a constrained Transformation surface

Artio treats Python/Polars Workflow definitions as canonical. To reconcile a changed definition, it loads the managed module in an isolated local worker, where ordinary top-level Python may perform author-controlled Module setup. Module setup is executable but is not part of the Workflow graph and Artio neither interprets nor structurally rewrites it.

Managed decorators register Sources, Transformations, and Outputs. Transformation parameter annotations declare graph dependencies, initially through `Annotated[pl.LazyFrame, Depends(node)]`; Artio resolves this metadata in the worker after loading the module, supporting both direct and postponed annotations. Artio then parses only registered Transformation bodies for the controlled Polars editing surface: common `LazyFrame` transformations and `when`/`then`/`otherwise` expressions. Unsupported bodies remain visible as opaque code-backed Transformations instead of being rewritten or discarded.

Import, declaration, annotation-resolution, or body-parsing failures produce Diagnostics. They do not cause the server process to execute workspace code or permit a structural edit over an invalid current definition.
