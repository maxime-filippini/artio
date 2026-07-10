"""Static discovery helpers for managed workflow modules."""

from __future__ import annotations

import ast

from artio.models import Diagnostic
from artio.models import DiagnosticSeverity
from artio.models import ManagedNode
from artio.models import ManagedNodeKind
from artio.models import ParseResult
from artio.models import SourcePosition
from artio.models import SourceSpan
from artio.models import WorkflowGraph

type FunctionDeclaration = ast.FunctionDef | ast.AsyncFunctionDef
type SourceLocatedNode = ast.expr | ast.stmt


def parse_workflow_definition(source: str, *, revision: int = 1) -> ParseResult:
    """Parse one managed Workflow definition without executing its source."""
    try:
        module = ast.parse(source)
    except SyntaxError as error:
        return ParseResult(
            workflow=None,
            diagnostics=(
                Diagnostic(
                    code="invalid-python",
                    message=error.msg,
                    severity=DiagnosticSeverity.ERROR,
                    span=_syntax_error_span(error),
                ),
            ),
        )

    workflow_binding = _find_workflow_binding(module)
    if workflow_binding is None:
        return ParseResult(
            workflow=None,
            diagnostics=(
                Diagnostic(
                    code="missing-workflow",
                    message="Expected one top-level Workflow declaration",
                    severity=DiagnosticSeverity.ERROR,
                ),
            ),
        )

    workflow_name, workflow_variable = workflow_binding
    nodes, diagnostics = _parse_managed_nodes(module, workflow_variable)
    return ParseResult(
        workflow=WorkflowGraph(
            name=workflow_name,
            revision=revision,
            nodes=nodes,
            edges=(),
        ),
        diagnostics=diagnostics,
    )


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
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
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
    match decorator:
        case ast.Call(func=decorator_function):
            return _matches_decorator(
                decorator_function,
                decorator_module=decorator_module,
                decorator_name=decorator_name,
            )
        case ast.Attribute(value=ast.Name(id=module), attr=name):
            return module == decorator_module and name == decorator_name
        case _:
            return False


def _find_workflow_binding(module: ast.Module) -> tuple[str, str] | None:
    bindings = tuple(
        binding
        for statement in module.body
        if (binding := _workflow_binding(statement)) is not None
    )
    return bindings[0] if len(bindings) == 1 else None


def _workflow_binding(statement: ast.stmt) -> tuple[str, str] | None:
    match statement:
        case ast.Assign(
            targets=[ast.Name(id=variable)],
            value=ast.Call(
                func=ast.Name(id="Workflow"),
                args=[ast.Constant(value=workflow_name)],
                keywords=[],
            ),
        ) if isinstance(workflow_name, str):
            return workflow_name, variable
        case _:
            return None


def _parse_managed_nodes(
    module: ast.Module, workflow_variable: str
) -> tuple[tuple[ManagedNode, ...], tuple[Diagnostic, ...]]:
    declarations = sorted(
        (
            *find_decorated_functions(
                module,
                decorator_module=workflow_variable,
                decorator_name="source",
            ),
            *find_decorated_functions(
                module,
                decorator_module=workflow_variable,
                decorator_name="transform",
            ),
        ),
        key=lambda declaration: (declaration.lineno, declaration.col_offset),
    )

    nodes: list[ManagedNode] = []
    diagnostics: list[Diagnostic] = []
    for declaration in declarations:
        parsed = _parse_node_declaration(declaration, workflow_variable)
        if isinstance(parsed, Diagnostic):
            diagnostics.append(parsed)
        else:
            nodes.append(parsed)

    return tuple(nodes), tuple(diagnostics)


def _parse_node_declaration(
    declaration: FunctionDeclaration, workflow_variable: str
) -> ManagedNode | Diagnostic:
    for decorator_name, kind in (
        ("source", ManagedNodeKind.SOURCE),
        ("transform", ManagedNodeKind.TRANSFORMATION),
    ):
        decorator = _matching_decorator(
            declaration,
            decorator_module=workflow_variable,
            decorator_name=decorator_name,
        )
        if decorator is not None:
            node_id = _literal_declaration_id(decorator)
            if node_id is None:
                return Diagnostic(
                    code="unsupported-managed-decorator",
                    message=(
                        f"@{workflow_variable}.{decorator_name} requires one "
                        "literal string ID"
                    ),
                    severity=DiagnosticSeverity.ERROR,
                    span=_source_span(decorator),
                )
            return ManagedNode(
                id=node_id,
                kind=kind,
                function_name=declaration.name,
                span=_declaration_span(declaration),
            )

    raise AssertionError("A discovered declaration must have a matching decorator")


def _matching_decorator(
    declaration: FunctionDeclaration, *, decorator_module: str, decorator_name: str
) -> ast.expr | None:
    return next(
        (
            decorator
            for decorator in declaration.decorator_list
            if _matches_decorator(
                decorator,
                decorator_module=decorator_module,
                decorator_name=decorator_name,
            )
        ),
        None,
    )


def _literal_declaration_id(decorator: ast.expr) -> str | None:
    match decorator:
        case ast.Call(
            args=[ast.Constant(value=node_id)],
            keywords=[],
        ) if isinstance(node_id, str):
            return node_id
        case _:
            return None


def _declaration_span(declaration: FunctionDeclaration) -> SourceSpan:
    start = min(
        (_source_position(decorator) for decorator in declaration.decorator_list),
        default=_source_position(declaration),
    )
    return SourceSpan(start=start, end=_source_end_position(declaration))


def _syntax_error_span(error: SyntaxError) -> SourceSpan | None:
    if error.lineno is None:
        return None

    start = SourcePosition(line=error.lineno, column=max((error.offset or 1) - 1, 0))
    end = SourcePosition(
        line=error.end_lineno or error.lineno,
        column=max((error.end_offset or error.offset or 1) - 1, 0),
    )
    return SourceSpan(start=start, end=end)


def _source_span(node: SourceLocatedNode) -> SourceSpan:
    return SourceSpan(start=_source_position(node), end=_source_end_position(node))


def _source_position(node: SourceLocatedNode) -> SourcePosition:
    return SourcePosition(line=node.lineno, column=node.col_offset)


def _source_end_position(node: SourceLocatedNode) -> SourcePosition:
    if node.end_lineno is None or node.end_col_offset is None:
        raise ValueError("A parsed source node must have an end position")
    return SourcePosition(line=node.end_lineno, column=node.end_col_offset)
