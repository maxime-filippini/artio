"""The on-disk configuration for an Artio workspace."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w


@dataclass(frozen=True)
class SourceFixtureBinding:
    """The Fixture used to preview one Source in a managed Workflow."""

    source_id: str
    fixture_id: str


@dataclass(frozen=True)
class WorkflowConfig:
    """A workflow module managed by a workspace."""

    name: str
    path: Path
    source_fixture_bindings: tuple[SourceFixtureBinding, ...] = ()

    def __post_init__(self) -> None:
        source_ids = [binding.source_id for binding in self.source_fixture_bindings]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("A Source may have only one Fixture binding")

    def fixture_for_source(self, source_id: str) -> str | None:
        return next(
            (
                binding.fixture_id
                for binding in self.source_fixture_bindings
                if binding.source_id == source_id
            ),
            None,
        )


@dataclass(frozen=True)
class Config:
    """Minimal explicit manifest used to identify managed modules."""

    workflows: tuple[WorkflowConfig, ...]
    version: int = 1

    def to_toml(self) -> str:
        """Return the manifest in the stable format written by ``artio init``."""
        lines = ["[workspace]", f"version = {self.version}"]

        for workflow in self.workflows:
            lines.extend(
                (
                    "",
                    "[[workflow]]",
                    f"name = {_toml_value(workflow.name)}",
                    f"path = {_toml_value(workflow.path.as_posix())}",
                )
            )
            if workflow.source_fixture_bindings:
                lines.extend(("", "[workflow.source_fixture]"))
                lines.extend(
                    f"{binding.source_id} = {_toml_value(binding.fixture_id)}"
                    for binding in workflow.source_fixture_bindings
                )

        return "\n".join(lines) + "\n"

    @classmethod
    def read_toml(cls, path: Path) -> Config:
        """Load managed Workflow and Preview bindings from a workspace manifest."""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=data["workspace"]["version"],
            workflows=tuple(
                WorkflowConfig(
                    name=workflow["name"],
                    path=Path(workflow["path"]),
                    source_fixture_bindings=tuple(
                        SourceFixtureBinding(
                            source_id=source_id,
                            fixture_id=fixture_id,
                        )
                        for source_id, fixture_id in workflow.get(
                            "source_fixture", {}
                        ).items()
                    ),
                )
                for workflow in data["workflow"]
            ),
        )

    def write_toml(self, path: Path) -> None:
        """Write the manifest to *path*.

        Callers are responsible for choosing a path that may safely be replaced.
        Keeping that policy outside this method also makes the serializer useful to
        later workspace-editing operations.
        """
        path.write_text(self.to_toml(), encoding="utf-8")


def _toml_value(value: str) -> str:
    """Encode a string with the manifest writer's TOML quoting rules."""
    return tomli_w.dumps({"value": value}).split("=", maxsplit=1)[1].strip()
