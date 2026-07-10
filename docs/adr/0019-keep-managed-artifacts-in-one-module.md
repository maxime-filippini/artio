# Keep managed artifacts in one module

In the first release, Fixtures, Decision trees, and Workflows that reference one another live in a single managed Python module. Cross-module imports and shared expression libraries are deferred so static parsing, source rewriting, and isolated Preview execution have one explicit local boundary.
