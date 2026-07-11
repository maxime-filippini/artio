from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl
import pytest
from click.testing import CliRunner

from artio.cli import cli
from artio.config import Config
from artio.config import SourceFixtureBinding
from artio.workspace import WORKFLOW_TEMPLATE
from artio.workspace import Workspace
from artio.workspace import WorkspaceAlreadyInitializedError


def test_initialize_writes_manifest_and_parseable_workflow(tmp_path: Path) -> None:
    workspace = Workspace.initialize(tmp_path / "demo")

    assert workspace.manifest_path.read_text(encoding="utf-8") == (
        "[workspace]\n"
        "version = 1\n"
        "\n"
        "[[workflow]]\n"
        'name = "main"\n'
        'path = "workflow.py"\n'
        "\n"
        "[workflow.source_fixture]\n"
        'source = "source"\n'
    )
    assert workspace.workflow_path.read_text(encoding="utf-8") == WORKFLOW_TEMPLATE
    assert pl.read_parquet(workspace.fixture_path).to_dicts() == [
        {"id": 1, "value": "first"},
        {"id": 2, "value": "second"},
        {"id": 3, "value": "third"},
    ]

    specification = importlib.util.spec_from_file_location(
        "artio_test_workflow", workspace.workflow_path
    )
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assert module.workflow.outputs == {"result": module.identity}
    assert module.workflow.fixtures == {"source": module.source_fixture}
    assert module.workflow.decision_trees == {"source-tier": module.source_tier}
    config = Config.read_toml(workspace.manifest_path)
    assert config.workflows[0].source_fixture_bindings == (
        SourceFixtureBinding(source_id="source", fixture_id="source"),
    )


def test_initialize_does_not_replace_existing_managed_file(tmp_path: Path) -> None:
    manifest = tmp_path / "artio.toml"
    manifest.write_text("do not replace", encoding="utf-8")

    with pytest.raises(WorkspaceAlreadyInitializedError):
        Workspace.initialize(tmp_path)

    assert manifest.read_text(encoding="utf-8") == "do not replace"
    assert not (tmp_path / "workflow.py").exists()


def test_initialize_force_replaces_existing_managed_files(tmp_path: Path) -> None:
    manifest = tmp_path / "artio.toml"
    workflow = tmp_path / "workflow.py"
    manifest.write_text("old manifest", encoding="utf-8")
    workflow.write_text("old workflow", encoding="utf-8")
    fixture = tmp_path / "fixtures" / "source.parquet"
    fixture.parent.mkdir()
    fixture.write_bytes(b"old fixture")

    workspace = Workspace.initialize(tmp_path, force=True)

    assert workspace.manifest_path.read_text(encoding="utf-8") != "old manifest"
    assert workspace.workflow_path.read_text(encoding="utf-8") == WORKFLOW_TEMPLATE
    assert pl.read_parquet(workspace.fixture_path).height == 3


def test_initialize_force_preserves_existing_files_when_staging_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "artio.toml"
    workflow = tmp_path / "workflow.py"
    manifest.write_text("old manifest", encoding="utf-8")
    workflow.write_text("old workflow", encoding="utf-8")

    def fail_to_write_manifest(self: Config, path: Path) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(Config, "write_toml", fail_to_write_manifest)

    with pytest.raises(OSError, match="write failed"):
        Workspace.initialize(tmp_path, force=True)

    assert manifest.read_text(encoding="utf-8") == "old manifest"
    assert workflow.read_text(encoding="utf-8") == "old workflow"


def test_cli_reports_an_existing_workspace_as_an_error(tmp_path: Path) -> None:
    Workspace.initialize(tmp_path)

    result = CliRunner().invoke(cli, ["init", str(tmp_path)])

    assert result.exit_code == 1
    assert "Refusing to overwrite existing file" in result.output


def test_cli_parse_displays_edges_and_diagnostics(tmp_path: Path) -> None:
    definition = tmp_path / "workflow.py"
    definition.write_text(
        """\
workflow = Workflow("main")

@workflow.transform("clean-orders")
def clean_orders(): pass

workflow.output("result", clean_orders)
workflow.output("broken", missing)
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["parse", str(definition)])

    assert result.exit_code == 0
    assert "'clean-orders' -> 'result'" in result.output
    assert "Diagnostics:" in result.output
    assert "unknown-output-target" in result.output


def test_cli_parse_displays_fixtures(tmp_path: Path) -> None:
    definition = tmp_path / "workflow.py"
    definition.write_text(
        """\
import polars as pl

workflow = Workflow("main")

@workflow.fixture("orders")
def orders_fixture() -> pl.LazyFrame:
    return pl.scan_parquet("fixtures/orders.parquet")
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["parse", str(definition)])

    assert result.exit_code == 0
    assert "Fixtures:" in result.output
    assert "'orders': 'fixtures/orders.parquet'" in result.output


def test_cli_parse_displays_decision_trees(tmp_path: Path) -> None:
    definition = tmp_path / "workflow.py"
    definition.write_text(
        """\
import polars as pl

workflow = Workflow("main")

@workflow.decision_tree("order-tier")
def order_tier(amount: pl.Expr) -> pl.Expr:
    return pl.when(amount > 100).then(pl.lit("priority")).otherwise("standard")
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["parse", str(definition)])

    assert result.exit_code == 0
    assert "Decision trees:" in result.output
    assert "'order-tier' (1 branches)" in result.output


def test_cli_force_replaces_an_existing_workspace(tmp_path: Path) -> None:
    Workspace.initialize(tmp_path)

    result = CliRunner().invoke(cli, ["init", "--force", str(tmp_path)])

    assert result.exit_code == 0
    assert "Initialized Artio workspace" in result.output
