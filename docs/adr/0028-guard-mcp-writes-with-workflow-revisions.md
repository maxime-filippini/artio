# Guard MCP writes with workflow revisions

Each Artio MCP mutation requires the caller's expected Workflow revision. Artio applies a mutation only when the revision matches, then returns the exact source diff and new revision; stale callers must reread rather than silently overwrite concurrent user or agent edits.
