from __future__ import annotations

import ast

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
    ]
    assert result.workflow.edges == ()
    assert (
        result.workflow.nodes[0].span.start.line
        < result.workflow.nodes[0].span.end.line
    )


def test_parse_workflow_definition_reports_invalid_python() -> None:
    result = parse_workflow_definition("workflow = Workflow(\n")

    assert result.workflow is None
    assert result.diagnostics[0].code == "invalid-python"
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
    assert result.diagnostics[0].code == "unsupported-managed-decorator"
