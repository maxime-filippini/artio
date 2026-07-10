# Declare reusable fixtures with decorators

Artio declares named Fixtures through a dedicated decorator in the Workflow definition, allowing Decision trees and Workflow sources to reference the same local Parquet sample data. Initial Fixtures are direct `pl.scan_parquet(...)` declarations only. Consumer-specific parameter bindings stay at the use site, rather than duplicating fixture paths and bindings in every declaration.
