"""Static discovery helpers for managed workflow modules."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from artio.models import DeclaredEdge
from artio.models import Diagnostic
from artio.models import DiagnosticCode
from artio.models import DiagnosticSeverity
from artio.models import Fixture
from artio.models import ManagedNode
from artio.models import ManagedNodeKind
from artio.models import ParseResult
from artio.models import SourcePosition
from artio.models import SourceSpan
from artio.models import WorkflowGraph

type FunctionDeclaration = ast.FunctionDef | ast.AsyncFunctionDef
type SourceLocatedNode = ast.expr | ast.stmt


@dataclass(frozen=True)
class _ParsedManagedNode:
    node: ManagedNode
    declaration: FunctionDeclaration


@dataclass(frozen=True)
class _ParsedOutput:
    node: ManagedNode
    target_func_name: str


def parse_workflow_definition(source: str, *, revision: int = 1) -> ParseResult:
    """Parse one managed Workflow definition without executing its source."""
    try:
        module = ast.parse(source)
    except SyntaxError as error:
        return ParseResult(
            workflow=None,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_PYTHON,
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
                    code=DiagnosticCode.MISSING_WORKFLOW,
                    message="Expected one top-level Workflow declaration",
                    severity=DiagnosticSeverity.ERROR,
                ),
            ),
        )

    workflow_name, workflow_variable = workflow_binding
    fixtures, fixture_diagnostics = _parse_fixtures(module, workflow_variable)
    parsed_nodes, diagnostics = _parse_managed_nodes(module, workflow_variable)
    parsed_outputs, output_diagnostics = _parse_outputs(module, workflow_variable)
    dependency_edges, edge_diagnostics = _parse_declared_edges(parsed_nodes)
    output_edges, output_edge_diagnostics = _parse_output_edges(
        parsed_outputs,
        parsed_nodes,
    )
    return ParseResult(
        workflow=WorkflowGraph(
            name=workflow_name,
            revision=revision,
            nodes=tuple(
                sorted(
                    (
                        *(parsed.node for parsed in parsed_nodes),
                        *(parsed.node for parsed in parsed_outputs),
                    ),
                    key=lambda node: node.span.start,
                )
            ),
            edges=(*dependency_edges, *output_edges),
        ),
        diagnostics=(
            *fixture_diagnostics,
            *diagnostics,
            *output_diagnostics,
            *edge_diagnostics,
            *output_edge_diagnostics,
        ),
        fixtures=fixtures,
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
) -> tuple[tuple[_ParsedManagedNode, ...], tuple[Diagnostic, ...]]:
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

    nodes: list[_ParsedManagedNode] = []
    diagnostics: list[Diagnostic] = []
    for declaration in declarations:
        parsed = _parse_node_declaration(declaration, workflow_variable)

        if isinstance(parsed, Diagnostic):
            diagnostics.append(parsed)
        else:
            nodes.append(_ParsedManagedNode(node=parsed, declaration=declaration))

    return tuple(nodes), tuple(diagnostics)


def _parse_fixtures(
    module: ast.Module, workflow_variable: str
) -> tuple[tuple[Fixture, ...], tuple[Diagnostic, ...]]:
    """Parse direct ``pl.scan_parquet`` Fixture declarations in source order."""
    fixtures: list[Fixture] = []
    diagnostics: list[Diagnostic] = []

    for declaration in find_decorated_functions(
        module,
        decorator_module=workflow_variable,
        decorator_name="fixture",
    ):
        parsed = _parse_fixture_declaration(declaration, workflow_variable)
        if isinstance(parsed, Diagnostic):
            diagnostics.append(parsed)
        else:
            fixtures.append(parsed)

    return tuple(fixtures), tuple(diagnostics)


def _parse_fixture_declaration(
    declaration: FunctionDeclaration, workflow_variable: str
) -> Fixture | Diagnostic:
    decorator = _matching_decorator(
        declaration,
        decorator_module=workflow_variable,
        decorator_name="fixture",
    )
    assert decorator is not None

    fixture_id = _literal_declaration_id(decorator)
    path = _fixture_path(declaration)
    if fixture_id is not None and path is not None:
        return Fixture(
            id=fixture_id,
            path=path,
            function_name=declaration.name,
            span=_declaration_span(declaration),
        )

    return Diagnostic(
        code=DiagnosticCode.UNSUPPORTED_FIXTURE_DECLARATION,
        message=(
            f"@{workflow_variable}.fixture requires one literal string ID and a "
            "body containing only return pl.scan_parquet(<literal path>)"
        ),
        severity=DiagnosticSeverity.ERROR,
        span=_declaration_span(declaration),
    )


def _fixture_path(declaration: FunctionDeclaration) -> str | None:
    body = declaration.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]

    match body:
        case [
            ast.Return(
                value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id="pl"), attr="scan_parquet"),
                    args=[ast.Constant(value=path), *_],
                )
            )
        ] if isinstance(path, str):
            return path
        case _:
            return None


def _parse_declared_edges(
    parsed_nodes: tuple[_ParsedManagedNode, ...],
) -> tuple[tuple[DeclaredEdge, ...], tuple[Diagnostic, ...]]:
    node_ids_by_function_name = {
        parsed.node.function_name: parsed.node.id
        for parsed in parsed_nodes
        if parsed.node.function_name is not None
    }
    edges: list[DeclaredEdge] = []
    diagnostics: list[Diagnostic] = []

    for parsed in parsed_nodes:
        if parsed.node.kind is not ManagedNodeKind.TRANSFORMATION:
            continue

        for parameter in _parameters(parsed.declaration):
            dependency = _depends_reference(parameter.annotation)
            if dependency is None:
                continue

            dependency_name, dependency_expression = dependency
            dependency_id = node_ids_by_function_name.get(dependency_name)
            if dependency_id is None:
                diagnostics.append(
                    Diagnostic(
                        code=DiagnosticCode.UNKNOWN_DEPENDENCY,
                        message=(
                            f"Transformation {parsed.node.id!r} depends on "
                            f"unknown declaration {dependency_name!r}"
                        ),
                        severity=DiagnosticSeverity.ERROR,
                        span=_source_span(dependency_expression),
                    )
                )
                continue

            edges.append(
                DeclaredEdge(
                    source_id=dependency_id,
                    target_id=parsed.node.id,
                )
            )

    return tuple(edges), tuple(diagnostics)


def _parse_outputs(
    module: ast.Module, workflow_variable: str
) -> tuple[tuple[_ParsedOutput, ...], tuple[Diagnostic, ...]]:
    outputs: list[_ParsedOutput] = []
    diagnostics: list[Diagnostic] = []

    for statement in module.body:
        match statement:
            case ast.Expr(value=ast.Call() as call) if _matches_decorator(
                call,
                decorator_module=workflow_variable,
                decorator_name="output",
            ):
                output = _parse_output_declaration(call, workflow_variable)

                if isinstance(output, Diagnostic):
                    diagnostics.append(output)
                else:
                    outputs.append(output)

    return tuple(outputs), tuple(diagnostics)


def _parse_output_declaration(
    call: ast.Call, workflow_variable: str
) -> _ParsedOutput | Diagnostic:
    match call:
        case ast.Call(
            args=[ast.Constant(value=output_id), ast.Name(id=target_func_name)],
            keywords=[],
        ) if isinstance(output_id, str):
            return _ParsedOutput(
                node=ManagedNode(
                    id=output_id,
                    kind=ManagedNodeKind.OUTPUT,
                    span=_source_span(call),
                ),
                target_func_name=target_func_name,
            )
        case _:
            return Diagnostic(
                code=DiagnosticCode.UNSUPPORTED_OUTPUT_DECLARATION,
                message=(
                    f"{workflow_variable}.output requires a literal output ID and a "
                    "direct Transformation reference"
                ),
                severity=DiagnosticSeverity.ERROR,
                span=_source_span(call),
            )


def _parse_output_edges(
    parsed_outputs: tuple[_ParsedOutput, ...],
    parsed_nodes: tuple[_ParsedManagedNode, ...],
) -> tuple[tuple[DeclaredEdge, ...], tuple[Diagnostic, ...]]:
    transformations_by_function_name = {
        parsed.node.function_name: parsed.node.id
        for parsed in parsed_nodes
        if parsed.node.kind is ManagedNodeKind.TRANSFORMATION
        and parsed.node.function_name is not None
    }

    edges: list[DeclaredEdge] = []
    diagnostics: list[Diagnostic] = []

    for output in parsed_outputs:
        target_id = transformations_by_function_name.get(output.target_func_name)

        if target_id is None:
            diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.UNKNOWN_OUTPUT_TARGET,
                    message=(
                        f"Output {output.node.id!r} targets unknown declaration "
                        f"{output.target_func_name!r}"
                    ),
                    severity=DiagnosticSeverity.ERROR,
                    span=output.node.span,
                )
            )
            continue

        edges.append(
            DeclaredEdge(
                source_id=target_id,
                target_id=output.node.id,
            )
        )

    return tuple(edges), tuple(diagnostics)


def _parameters(declaration: FunctionDeclaration) -> tuple[ast.arg, ...]:
    return (
        *declaration.args.posonlyargs,
        *declaration.args.args,
        *declaration.args.kwonlyargs,
    )


def _depends_reference(
    annotation: ast.expr | None,
) -> tuple[str, ast.expr] | None:
    match annotation:
        case ast.Subscript(
            value=ast.Name(id="Annotated"),
            slice=ast.Tuple(elts=[_, *metadata]),
        ):
            return next(
                (
                    dependency
                    for item in metadata
                    if (dependency := _depends_call(item)) is not None
                ),
                None,
            )
        case _:
            return None


def _depends_call(expression: ast.expr) -> tuple[str, ast.expr] | None:
    match expression:
        case ast.Call(
            func=ast.Name(id="Depends"),
            args=[ast.Name(id=dependency_name)],
            keywords=[],
        ):
            return dependency_name, expression
        case _:
            return None


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
                    code=DiagnosticCode.UNSUPPORTED_MANAGED_DECORATOR,
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
