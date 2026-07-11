from __future__ import annotations

from pathlib import Path

import pytest

from artio.config import Config
from artio.config import SourceFixtureBinding
from artio.config import WorkflowConfig


def test_workflow_config_resolves_each_sources_fixture() -> None:
    workflow = WorkflowConfig(
        name="main",
        path=Path("workflow.py"),
        source_fixture_bindings=(
            SourceFixtureBinding(source_id="orders", fixture_id="orders-sample"),
            SourceFixtureBinding(source_id="customers", fixture_id="customers-sample"),
        ),
    )

    assert workflow.fixture_for_source("orders") == "orders-sample"
    assert workflow.fixture_for_source("missing") is None


def test_workflow_config_rejects_multiple_fixture_bindings_for_one_source() -> None:
    with pytest.raises(ValueError, match="only one Fixture"):
        WorkflowConfig(
            name="main",
            path=Path("workflow.py"),
            source_fixture_bindings=(
                SourceFixtureBinding(source_id="orders", fixture_id="orders-a"),
                SourceFixtureBinding(source_id="orders", fixture_id="orders-b"),
            ),
        )


def test_config_round_trips_source_fixture_bindings(tmp_path: Path) -> None:
    config = Config(
        workflows=(
            WorkflowConfig(
                name="main",
                path=Path("workflow.py"),
                source_fixture_bindings=(
                    SourceFixtureBinding(
                        source_id="orders", fixture_id="orders-sample"
                    ),
                ),
            ),
        ),
    )
    manifest = tmp_path / "artio.toml"

    config.write_toml(manifest)

    assert Config.read_toml(manifest) == config
