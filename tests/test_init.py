from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from click.testing import CliRunner

from artio.cli import cli
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
    assert module.workflow.outputs == {"result": "identity"}


def test_initialize_does_not_replace_existing_managed_file(tmp_path: Path) -> None:
    manifest = tmp_path / "artio.toml"
    manifest.write_text("do not replace", encoding="utf-8")

    with pytest.raises(WorkspaceAlreadyInitializedError):
        Workspace.initialize(tmp_path)

    assert manifest.read_text(encoding="utf-8") == "do not replace"
    assert not (tmp_path / "workflow.py").exists()


def test_cli_reports_an_existing_workspace_as_an_error(tmp_path: Path) -> None:
    Workspace.initialize(tmp_path)

    result = CliRunner().invoke(cli, ["init", str(tmp_path)])

    assert result.exit_code == 1
    assert "Refusing to overwrite existing file" in result.output
