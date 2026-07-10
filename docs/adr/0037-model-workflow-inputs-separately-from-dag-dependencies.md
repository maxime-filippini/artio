# Model Workflow inputs separately from DAG dependencies

A Workflow declares one typed Workflow input schema whose validated values are supplied for each Preview or other execution. Sources and Transformations may consume those values explicitly, but they are execution context rather than graph nodes or `Depends(...)` edges; Artio therefore parses, validates, and exposes input consumers separately from the Workflow DAG, and identifies Preview results by both Workflow revision and normalized input values.
