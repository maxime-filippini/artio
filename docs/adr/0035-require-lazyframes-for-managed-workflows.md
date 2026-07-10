# Require LazyFrames for managed workflows

Managed Artio Sources and Transformations accept and return Polars `LazyFrame` values. This enables schema planning, dependency-slice Preview execution, and bounded collection; eager `DataFrame` operations may exist only inside opaque or custom code outside Artio's managed visual guarantees.
