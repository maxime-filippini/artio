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
    assert [decision_tree.id for decision_tree in result.decision_trees] == [
        "source-tier"
    ]
    assert [
        (
            workflow_input.id,
            workflow_input.type_expression,
            workflow_input.default_expression,
        )
        for workflow_input in result.workflow.inputs
    ] == [("minimum_value", "int", "1")]
    assert [
        (consumer.input_id, consumer.node_id, consumer.parameter_name)
        for consumer in result.workflow.input_consumers
    ] == [("minimum_value", "identity", "minimum_value")]
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


def test_parse_workflow_definition_builds_decision_tree_branch_structure() -> None:
    result = parse_workflow_definition(
        '''\
import polars as pl

workflow = Workflow("main")

@workflow.decision_tree("order-tier")
def order_tier(amount: pl.Expr, blocked: pl.Expr) -> pl.Expr:
    """Classify an order without interpreting its branch expressions."""
    return (
        pl.when((amount > 100) & blocked.not_())
        .then(pl.lit("priority"))
        .when(amount.is_null())
        .then(default_tier(amount))
        .otherwise(pl.lit("standard"))
    )
'''
    )

    assert result.diagnostics == ()
    assert len(result.decision_trees) == 1
    decision_tree = result.decision_trees[0]
    assert decision_tree.id == "order-tier"
    assert decision_tree.function_name == "order_tier"
    assert decision_tree.parameters == ("amount", "blocked")
    assert len(decision_tree.branches) == 2
    assert decision_tree.branches[0].condition_span.start.line == 9
    assert decision_tree.branches[1].result_span.start.line == 12
    assert decision_tree.otherwise_span.start.line == 13


def test_parse_workflow_definition_requires_decision_tree_otherwise() -> None:
    result = parse_workflow_definition(
        """\
import polars as pl

workflow = Workflow("main")

@workflow.decision_tree("order-tier")
def order_tier(amount: pl.Expr) -> pl.Expr:
    return pl.when(amount > 100).then(pl.lit("priority"))
"""
    )

    assert result.decision_trees == ()
    assert (
        result.diagnostics[0].code
        is DiagnosticCode.UNSUPPORTED_DECISION_TREE_DECLARATION
    )


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


def test_parse_workflow_definition_captures_pydantic_inputs_and_consumers() -> None:
    result = parse_workflow_definition(
        """\
from typing import Annotated

from pydantic import BaseModel

class RunInputs(BaseModel):
    region: str = "EU"
    minimum_value: int

workflow = Workflow("main", inputs=RunInputs)

@workflow.transform("clean-orders")
def clean_orders(
    region: Annotated[str, workflow.input("region")],
    minimum_value: Annotated[int, workflow.input("minimum_value")],
): pass
"""
    )

    assert result.diagnostics == ()
    assert result.workflow is not None
    assert [
        (
            workflow_input.id,
            workflow_input.type_expression,
            workflow_input.default_expression,
        )
        for workflow_input in result.workflow.inputs
    ] == [("region", "str", "'EU'"), ("minimum_value", "int", None)]
    assert [
        (consumer.input_id, consumer.node_id, consumer.parameter_name)
        for consumer in result.workflow.input_consumers
    ] == [
        ("region", "clean-orders", "region"),
        ("minimum_value", "clean-orders", "minimum_value"),
    ]
    assert result.workflow.edges == ()


def test_parse_workflow_definition_reports_unknown_workflow_input_consumers() -> None:
    result = parse_workflow_definition(
        """\
from typing import Annotated

from pydantic import BaseModel

class RunInputs(BaseModel):
    region: str

workflow = Workflow("main", inputs=RunInputs)

@workflow.transform("clean-orders")
def clean_orders(
    country: Annotated[str, workflow.input("country")],
): pass
"""
    )

    assert result.workflow is not None
    assert result.workflow.input_consumers == ()
    assert result.diagnostics[0].code is DiagnosticCode.UNKNOWN_WORKFLOW_INPUT


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
