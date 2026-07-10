# Verify decision trees with reusable Parquet fixtures

A Decision tree is marked verified only after its current revision successfully executes against a named local Parquet Fixture with explicit Tree parameter bindings, displaying its schema and bounded result rows. Fixtures are reusable by Decision trees and Workflow sources. Initial verification is execution-based rather than assertion-based; use-specific workflow Preview diagnostics remain separate.
