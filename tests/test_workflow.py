from __future__ import annotations

import polars as pl

from artio import DecisionTree
from artio import Fixture
from artio import Workflow


def test_fixture_decorator_registers_a_named_lazy_frame_declaration() -> None:
    workflow = Workflow("main")

    @workflow.fixture("orders")
    def orders() -> pl.LazyFrame:
        return pl.LazyFrame({"order_id": [1]})

    assert isinstance(orders, Fixture)
    assert orders.id == "orders"
    assert workflow.fixtures == {"orders": orders}


def test_fixture_decorator_replaces_an_existing_fixture_with_the_same_id() -> None:
    workflow = Workflow("main")

    @workflow.fixture("orders")
    def initial_orders() -> pl.LazyFrame:
        return pl.LazyFrame()

    @workflow.fixture("orders")
    def replacement_orders() -> pl.LazyFrame:
        return pl.LazyFrame()

    assert workflow.fixtures == {"orders": replacement_orders}
    assert initial_orders is not replacement_orders


def test_decision_tree_decorator_registers_a_reusable_expression() -> None:
    workflow = Workflow("main")

    @workflow.decision_tree("order-tier")
    def order_tier(amount: pl.Expr) -> pl.Expr:
        return pl.when(amount > 100).then(pl.lit("priority")).otherwise("standard")

    assert isinstance(order_tier, DecisionTree)
    assert order_tier.id == "order-tier"
    assert workflow.decision_trees == {"order-tier": order_tier}
