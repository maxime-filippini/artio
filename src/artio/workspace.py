"""Workspace creation and layout constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artio.config import Config
from artio.config import WorkflowConfig

MANIFEST_FILENAME = "artio.toml"
DEFAULT_WORKFLOW_FILENAME = "workflow.py"
DEFAULT_WORKFLOW_NAME = "main"

WORKFLOW_TEMPLATE = '''\
from typing import Annotated

import polars as pl

from artio import Depends
from artio import Workflow

workflow = Workflow("main")


@workflow.source("source")
def source() -> pl.LazyFrame:
    """Declare the source used by previews."""
    return pl.LazyFrame()


@workflow.transform("identity")
def identity(source: Annotated[pl.LazyFrame, Depends(source)]) -> pl.LazyFrame:
    """Add Polars transformations here."""
    return source


workflow.output("result", "identity")

'''


class WorkspaceAlreadyInitializedError(FileExistsError):
    """Raised when initialization would replace an existing workspace file."""


@dataclass(frozen=True)
class Workspace:
    path: Path

    @property
    def manifest_path(self) -> Path:
        return self.path / MANIFEST_FILENAME

    @property
    def workflow_path(self) -> Path:
        return self.path / DEFAULT_WORKFLOW_FILENAME

    @classmethod
    def initialize(cls, path: Path) -> Workspace:
        """Create the smallest usable Artio workspace without overwriting files."""
        workspace = cls(path.expanduser().resolve())

        if workspace.path.exists() and not workspace.path.is_dir():
            raise NotADirectoryError(
                f"Workspace path is not a directory: {workspace.path}"
            )

        # Check before making a directory so a failed initialization is side-effect
        # free for an existing workspace.
        for candidate in (workspace.manifest_path, workspace.workflow_path):
            if candidate.exists():
                raise WorkspaceAlreadyInitializedError(
                    f"Refusing to overwrite existing file: {candidate}"
                )

        workspace.path.mkdir(parents=True, exist_ok=True)
        config = Config(
            workflows=(
                WorkflowConfig(
                    name=DEFAULT_WORKFLOW_NAME,
                    path=Path(DEFAULT_WORKFLOW_FILENAME),
                ),
            )
        )

        try:
            config.write_toml(workspace.manifest_path)
            workspace.workflow_path.write_text(WORKFLOW_TEMPLATE, encoding="utf-8")
        except Exception:
            # Do not leave a half-created managed workspace when a write fails.
            for candidate in (workspace.manifest_path, workspace.workflow_path):
                if candidate.exists():
                    candidate.unlink()
            raise

        return workspace
