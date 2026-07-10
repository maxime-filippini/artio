# Use stdio for the initial MCP transport

The initial Artio MCP server runs through standard input/output as `artio mcp <workspace>`. This is easy for agent clients to register, scopes each process to an explicit Workspace, and avoids a separate local HTTP authentication boundary; streamable HTTP is deferred until remote integration needs it.
