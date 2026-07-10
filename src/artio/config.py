"""The on-disk configuration for an Artio workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tomli_w


@dataclass(frozen=True)
class WorkflowConfig:
    """A workflow module managed by a workspace."""

    name: str
    path: Path


@dataclass(frozen=True)
class Config:
    """Minimal explicit manifest used to identify managed modules."""

    workflows: tuple[WorkflowConfig, ...]
    version: int = 1

    def to_toml(self) -> str:
        """Return the manifest in the stable format written by ``artio init``."""
        return tomli_w.dumps(
            {
                "workspace": {"version": self.version},
                "workflow": [
                    {"name": workflow.name, "path": workflow.path.as_posix()}
                    for workflow in self.workflows
                ],
            }
        )

    def write_toml(self, path: Path) -> None:
        """Write the manifest to *path*.

        Callers are responsible for choosing a path that may safely be replaced.
        Keeping that policy outside this method also makes the serializer useful to
        later workspace-editing operations.
        """
        path.write_text(self.to_toml(), encoding="utf-8")
