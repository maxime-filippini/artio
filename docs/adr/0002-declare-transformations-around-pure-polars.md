# Declare transformations around pure Polars

Artio workflows declare sources, transformations, and outputs through its authoring API, while each Transformation body is ordinary Polars code over supplied lazy frames. This makes graph identity and dependencies explicit without requiring Artio to replace or emulate the Polars API; undeclared or dynamic Python remains possible but is not guaranteed to be graph-editable.
