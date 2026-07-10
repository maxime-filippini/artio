"""Static discovery helpers for managed Artio workflow modules."""

from __future__ import annotations

import ast

type FunctionDeclaration = ast.FunctionDef | ast.AsyncFunctionDef


def find_decorated_functions(
    module: ast.Module, *, decorator_module: str, decorator_name: str
) -> tuple[FunctionDeclaration, ...]:
    """Return top-level functions using ``@module.name`` in source order.

    The decorator may be called (as in ``@workflow.source("orders")``) or used
    directly. This deliberately matches only a simple name followed by an
    attribute: aliases, imports, and dynamic decorator expressions are outside
    the managed syntax until the parser learns how to resolve them.
    """
    return tuple(
        statement
        for statement in module.body
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            _matches_decorator(
                decorator,
                decorator_module=decorator_module,
                decorator_name=decorator_name,
            )
            for decorator in statement.decorator_list
        )
    )


def _matches_decorator(
    decorator: ast.expr, *, decorator_module: str, decorator_name: str
) -> bool:
    if isinstance(decorator, ast.Call):
        decorator = decorator.func

    return (
        isinstance(decorator, ast.Attribute)
        and decorator.attr == decorator_name
        and isinstance(decorator.value, ast.Name)
        and decorator.value.id == decorator_module
    )
