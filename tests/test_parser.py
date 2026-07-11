from __future__ import annotations

import ast

import pytest

from artio.models import DeclaredEdge
from artio.models import DiagnosticCode
from artio.parser import find_decorated_functions
from artio.parser import parse_workflow_definition
from artio.workspace import WORKFLOW_TEMPLATE


def test_find_decorated_functions_returns_matching_top_level_functions_in_order() -> (
    None
):
    module = ast.parse(
        """
@workflow.transform("second")
def second(): pass

@workflow.source("orders")
def orders(): pass

@workflow.transform("third")
def third(): pass
"""
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="transform"
    )

    assert [function.name for function in functions] == ["second", "third"]


def test_find_decorated_functions_accepts_a_direct_decorator_reference() -> None:
    module = ast.parse(
        """
@workflow.source
def orders(): pass
"""
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="source"
    )

    assert [function.name for function in functions] == ["orders"]


def test_find_decorated_functions_excludes_dynamic_and_nested_decorators() -> None:
    module = ast.parse(
        """
@factory.workflow.transform("dynamic")
def dynamic(): pass

class Example:
    @workflow.transform("nested")
    def nested(self): pass

@workflow.source("orders")
def orders(): pass
"""
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="transform"
    )

    assert functions == ()


def test_parse_workflow_definition_builds_nodes_from_the_managed_template() -> None:
    result = parse_workflow_definition(WORKFLOW_TEMPLATE)

    assert result.diagnostics == ()
    assert result.workflow is not None
    assert result.workflow.name == "main"
    assert result.workflow.revision == 1
    assert [
        (node.id, node.kind, node.function_name) for node in result.workflow.nodes
    ] == [
        ("source", "source", "source"),
        ("identity", "transformation", "identity"),
        ("result", "output", None),
    ]
    assert result.workflow.edges == (
        DeclaredEdge(source_id="source", target_id="identity"),
        DeclaredEdge(source_id="identity", target_id="result"),
    )
    assert (
        result.workflow.nodes[0].span.start.line
        < result.workflow.nodes[0].span.end.line
    )


def test_parse_workflow_definition_builds_reusable_parquet_fixtures() -> None:
    result = parse_workflow_definition(
        """\
import polars as pl

workflow = Workflow("main")

@workflow.fixture("orders")
def orders_fixture() -> pl.LazyFrame:
    '''Sample orders used by previews.'''
    return pl.scan_parquet("fixtures/orders.parquet")
"""
    )

    assert result.diagnostics == ()
    assert [
        (fixture.id, fixture.path, fixture.function_name) for fixture in result.fixtures
    ] == [
        ("orders", "fixtures/orders.parquet", "orders_fixture"),
    ]
    assert result.fixtures[0].span.start.line == 5


@pytest.mark.parametrize(
    "body",
    [
        'return pl.scan_csv("fixtures/orders.csv")',
        'path = "fixtures/orders.parquet"\n    return pl.scan_parquet(path)',
        'return pl.scan_parquet("fixtures/orders.parquet").filter(pl.col("id") > 0)',
    ],
)
def test_parse_workflow_definition_rejects_unsupported_fixture_bodies(
    body: str,
) -> None:
    result = parse_workflow_definition(
        f"""\
import polars as pl

workflow = Workflow("main")

@workflow.fixture("orders")
def orders_fixture() -> pl.LazyFrame:
    {body}
"""
    )

    assert result.fixtures == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNSUPPORTED_FIXTURE_DECLARATION


def test_parse_workflow_definition_reports_invalid_python() -> None:
    result = parse_workflow_definition("workflow = Workflow(\n")

    assert result.workflow is None
    assert result.diagnostics[0].code is DiagnosticCode.INVALID_PYTHON
    assert result.diagnostics[0].span is not None


def test_parse_workflow_definition_reports_an_unsupported_declaration() -> None:
    result = parse_workflow_definition(
        """
workflow = Workflow("main")

@workflow.source(source_id)
def source(): pass
"""
    )

    assert result.workflow is not None
    assert result.workflow.nodes == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNSUPPORTED_MANAGED_DECORATOR


def test_parse_workflow_definition_resolves_dependencies_by_function_name() -> None:
    result = parse_workflow_definition(
        """
from typing import Annotated

workflow = Workflow("main")

@workflow.source("raw-orders")
def raw_orders(): pass

@workflow.transform("clean-orders")
def clean_orders(
    orders: Annotated[LazyFrame, Depends(raw_orders)],
): pass
"""
    )

    assert result.workflow is not None
    assert result.workflow.edges == (
        DeclaredEdge(source_id="raw-orders", target_id="clean-orders"),
    )


def test_parse_workflow_definition_reports_an_unknown_dependency() -> None:
    result = parse_workflow_definition(
        """
from typing import Annotated

workflow = Workflow("main")

@workflow.transform("clean-orders")
def clean_orders(
    orders: Annotated[LazyFrame, Depends(missing_source)],
): pass
"""
    )

    assert result.workflow is not None
    assert result.workflow.edges == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNKNOWN_DEPENDENCY


def test_parse_workflow_definition_reports_an_unknown_output_target() -> None:
    result = parse_workflow_definition(
        """
workflow = Workflow("main")

workflow.output("result", missing)
"""
    )

    assert result.workflow is not None
    assert [node.id for node in result.workflow.nodes] == ["result"]
    assert result.workflow.edges == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNKNOWN_OUTPUT_TARGET


def test_parse_workflow_definition_resolves_an_output_by_transformation_name() -> None:
    result = parse_workflow_definition(
        """
workflow = Workflow("main")

@workflow.transform("clean-orders")
def clean_orders(): pass

workflow.output("result", clean_orders)
"""
    )

    assert result.workflow is not None
    assert result.workflow.edges == (
        DeclaredEdge(source_id="clean-orders", target_id="result"),
    )
    assert result.diagnostics == ()


def test_parse_workflow_definition_rejects_a_source_as_an_output_target() -> None:
    result = parse_workflow_definition(
        """
workflow = Workflow("main")

@workflow.source("orders")
def orders(): pass

workflow.output("result", orders)
"""
    )

    assert result.workflow is not None
    assert [node.id for node in result.workflow.nodes] == ["orders", "result"]
    assert result.workflow.edges == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNKNOWN_OUTPUT_TARGET


@pytest.mark.parametrize("target", ['"clean-orders"', "None"])
def test_parse_workflow_definition_rejects_non_reference_output_targets(
    target: str,
) -> None:
    result = parse_workflow_definition(
        f"""\
workflow = Workflow("main")

workflow.output("result", {target})
"""
    )

    assert result.workflow is not None
    assert result.workflow.nodes == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNSUPPORTED_OUTPUT_DECLARATION
