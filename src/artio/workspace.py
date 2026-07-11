"""Workspace creation and layout constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import polars as pl

from artio.config import Config
from artio.config import WorkflowConfig

MANIFEST_FILENAME = "artio.toml"
DEFAULT_WORKFLOW_FILENAME = "workflow.py"
DEFAULT_WORKFLOW_NAME = "main"
DEFAULT_FIXTURE_PATH = Path("fixtures/source.parquet")

DEFAULT_FIXTURE_DATA = pl.DataFrame(
    {
        "id": [1, 2, 3],
        "value": ["first", "second", "third"],
    }
)

WORKFLOW_TEMPLATE = '''\
from typing import Annotated

import polars as pl

from artio import Depends
from artio import Workflow

workflow = Workflow("main")


@workflow.fixture("source")
def source_fixture() -> pl.LazyFrame:
    """Provide small local sample data for previews."""
    return pl.scan_parquet("fixtures/source.parquet")


@workflow.decision_tree("source-tier")
def source_tier(id: pl.Expr) -> pl.Expr:
    """Classify sample rows by their identifier."""
    return pl.when(id == 1).then(pl.lit("first")).otherwise(pl.lit("later"))


@workflow.source("source")
def source() -> pl.LazyFrame:
    """Declare the source used by previews."""
    return pl.LazyFrame()


@workflow.transform("identity")
def identity(source: Annotated[pl.LazyFrame, Depends(source)]) -> pl.LazyFrame:
    """Add Polars transformations here."""
    return source


workflow.output("result", identity)

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

    @property
    def fixture_path(self) -> Path:
        return self.path / DEFAULT_FIXTURE_PATH

    @classmethod
    def initialize(cls, path: Path, force: bool = False) -> Workspace:
        """Create the smallest usable Artio workspace, overwriting when forced."""
        workspace = cls(path.expanduser().resolve())

        if workspace.path.exists() and not workspace.path.is_dir():
            raise NotADirectoryError(
                f"Workspace path is not a directory: {workspace.path}"
            )

        # Check before making a directory so a failed initialization is side-effect
        # free for an existing workspace.
        for candidate in (
            workspace.manifest_path,
            workspace.workflow_path,
            workspace.fixture_path,
        ):
            if candidate.exists() and not force:
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

        # We write both files to temporary files
        manifest_temp: Path | None = None
        workflow_temp: Path | None = None
        fixture_temp: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=workspace.path,
                prefix=f".{MANIFEST_FILENAME}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                manifest_temp = Path(temporary_file.name)

            with NamedTemporaryFile(
                dir=workspace.path,
                prefix=f".{DEFAULT_WORKFLOW_FILENAME}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                workflow_temp = Path(temporary_file.name)

            with NamedTemporaryFile(
                dir=workspace.path,
                prefix=f".{DEFAULT_FIXTURE_PATH.stem}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                fixture_temp = Path(temporary_file.name)

            config.write_toml(manifest_temp)
            workflow_temp.write_text(WORKFLOW_TEMPLATE, encoding="utf-8")
            DEFAULT_FIXTURE_DATA.write_parquet(fixture_temp)

            manifest_temp.replace(workspace.manifest_path)
            workflow_temp.replace(workspace.workflow_path)
            workspace.fixture_path.parent.mkdir(parents=True, exist_ok=True)
            fixture_temp.replace(workspace.fixture_path)

        except Exception:
            # Never delete existing managed files after a failed forced init.
            for temporary_path in (manifest_temp, workflow_temp, fixture_temp):
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
            raise

        return workspace
