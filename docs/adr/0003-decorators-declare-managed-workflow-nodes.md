# Decorators declare managed workflow nodes

Artio identifies transformations through `@wf.transform(...)` decorators on Python functions, with similarly explicit declarations for sources and outputs. The decorator defines a stable, parseable graph boundary while the function body stays ordinary Polars; Artio changes only supported constructs inside managed nodes rather than rewriting the whole source file.
