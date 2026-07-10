# Preserve opaque transformation bodies

When Artio cannot interpret a syntactically valid Transformation body, it represents it as an Opaque transformation: its DAG node, declaration, and dependencies remain visible and editable, while body-level visual editing and Decision tree extraction are disabled. The original code stays intact and remains previewable.
