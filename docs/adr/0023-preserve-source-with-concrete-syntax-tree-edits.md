# Preserve source with concrete-syntax-tree edits

Artio may use Python AST analysis to discover managed constructs and emit diagnostics, but uses a concrete-syntax-tree rewriter for source edits. Managed edits preserve comments, formatting, and unrelated code rather than regenerating the entire module from an abstract syntax tree.
