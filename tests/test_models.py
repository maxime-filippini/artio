from __future__ import annotations

import pytest

from artio.models import DecisionTree
from artio.models import DecisionTreeBranch
from artio.models import DeclaredEdge
from artio.models import Fixture
from artio.models import ManagedNode
from artio.models import ManagedNodeKind
from artio.models import OpaqueBody
from artio.models import SourcePosition
from artio.models import SourceSpan
from artio.models import WorkflowGraph
from artio.models import WorkflowInput
from artio.models import WorkflowInputConsumer


def test_workflow_graph_captures_nodes_edges_and_revision() -> None:
    span = SourceSpan(
        start=SourcePosition(line=3, column=0),
        end=SourcePosition(line=5, column=17),
    )
    source = ManagedNode(
        id="orders",
        kind=ManagedNodeKind.SOURCE,
        function_name="orders",
        span=span,
    )
    transformation = ManagedNode(
        id="clean_orders",
        kind=ManagedNodeKind.TRANSFORMATION,
        function_name="clean_orders",
        span=span,
    )

    graph = WorkflowGraph(
        name="main",
        revision=1,
        nodes=(source, transformation),
        edges=(DeclaredEdge(source_id="orders", target_id="clean_orders"),),
    )

    assert graph.nodes == (source, transformation)
    assert graph.edges == (DeclaredEdge(source_id="orders", target_id="clean_orders"),)


def test_managed_node_retains_an_opaque_transformation_body() -> None:
    span = SourceSpan(
        start=SourcePosition(line=3, column=4),
        end=SourcePosition(line=4, column=16),
    )
    body = OpaqueBody(source="return orders", span=span)
    node = ManagedNode(
        id="clean-orders",
        kind=ManagedNodeKind.TRANSFORMATION,
        function_name="clean_orders",
        span=span,
        opaque_body=body,
    )

    assert node.opaque_body == body


def test_workflow_graph_captures_inputs_and_consumers_outside_the_dag() -> None:
    span = SourceSpan(
        start=SourcePosition(line=3, column=0),
        end=SourcePosition(line=3, column=20),
    )
    workflow_input = WorkflowInput(
        id="minimum_value",
        type_expression="int",
        default_expression="1",
        span=span,
    )
    consumer = WorkflowInputConsumer(
        input_id="minimum_value",
        node_id="clean-orders",
        parameter_name="minimum_value",
        span=span,
    )

    graph = WorkflowGraph(
        name="main",
        revision=1,
        nodes=(),
        edges=(),
        inputs=(workflow_input,),
        input_consumers=(consumer,),
    )

    assert graph.inputs == (workflow_input,)
    assert graph.input_consumers == (consumer,)


@pytest.mark.parametrize(
    ("line", "column", "message"),
    [
        (0, 0, "line must be at least 1"),
        (1, -1, "column cannot be negative"),
    ],
)
def test_source_position_requires_a_valid_location(
    line: int, column: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SourcePosition(line=line, column=column)


def test_source_span_rejects_an_end_before_its_start() -> None:
    with pytest.raises(ValueError, match="end cannot precede"):
        SourceSpan(
            start=SourcePosition(line=3, column=0),
            end=SourcePosition(line=2, column=0),
        )


def test_workflow_graph_requires_a_positive_revision() -> None:
    with pytest.raises(ValueError, match="revision must be at least 1"):
        WorkflowGraph(name="main", revision=0, nodes=(), edges=())


def test_fixture_captures_its_parquet_path_and_declaration_location() -> None:
    span = SourceSpan(
        start=SourcePosition(line=3, column=0),
        end=SourcePosition(line=5, column=17),
    )

    fixture = Fixture(
        id="orders",
        path="fixtures/orders.parquet",
        function_name="orders_fixture",
        span=span,
    )

    assert fixture.path == "fixtures/orders.parquet"


def test_decision_tree_captures_ordered_branch_spans() -> None:
    span = SourceSpan(
        start=SourcePosition(line=3, column=0),
        end=SourcePosition(line=5, column=17),
    )
    branch = DecisionTreeBranch(condition_span=span, result_span=span)

    decision_tree = DecisionTree(
        id="order-tier",
        function_name="order_tier",
        parameters=("amount",),
        branches=(branch,),
        otherwise_span=span,
        span=span,
    )

    assert decision_tree.branches == (branch,)
