# Sync the client with snapshots and events

On WebSocket connect or reconnect, Artio sends a complete revisioned Workspace snapshot. During a session it sends typed incremental events for workflow updates, preview completion, and diagnostic changes, allowing reliable recovery without repeatedly transmitting the whole Workspace.
