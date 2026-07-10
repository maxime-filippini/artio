# Retain stale state for invalid source

When a managed module is saved with a syntax error, Artio retains the last valid DAG and Preview marked stale, emits the current parse Diagnostic, and disables visual mutations until parsing succeeds. This preserves context without risking a source rewrite over an author or agent's repair.
