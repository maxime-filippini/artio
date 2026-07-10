from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from click.testing import CliRunner

from artio.cli import cli
from artio.config import Config
from artio.workspace import WORKFLOW_TEMPLATE
from artio.workspace import Workspace
from artio.workspace import WorkspaceAlreadyInitializedError


def test_initialize_writes_manifest_and_parseable_workflow(tmp_path: Path) -> None:
    workspace = Workspace.initialize(tmp_path / "demo")

    assert workspace.manifest_path.read_text(encoding="utf-8") == (
        'workflow = [\n    { name = "main", path = "workflow.py" },\n]\n\n'
        "[workspace]\nversion = 1\n"
    )
    assert workspace.workflow_path.read_text(encoding="utf-8") == WORKFLOW_TEMPLATE

    specification = importlib.util.spec_from_file_location(
        "artio_test_workflow", workspace.workflow_path
    )
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assert module.workflow.outputs == {"result": module.identity}


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

    workspace = Workspace.initialize(tmp_path, force=True)

    assert workspace.manifest_path.read_text(encoding="utf-8") != "old manifest"
    assert workspace.workflow_path.read_text(encoding="utf-8") == WORKFLOW_TEMPLATE


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


def test_cli_force_replaces_an_existing_workspace(tmp_path: Path) -> None:
    Workspace.initialize(tmp_path)

    result = CliRunner().invoke(cli, ["init", "--force", str(tmp_path)])

    assert result.exit_code == 0
    assert "Initialized Artio workspace" in result.output
