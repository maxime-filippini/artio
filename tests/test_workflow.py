from __future__ import annotations

import polars as pl

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
