# Manage DAG edges through declarations

Adding a DAG edge rewrites the receiving Transformation's managed input declaration and Python function signature, creating a safe skeleton where necessary. Removing or renaming an input requires confirmation because code in the function body may reference the affected parameter.
