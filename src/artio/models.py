"""Domain models produced while parsing a Workflow definition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, order=True)
class SourcePosition:
    """A zero-based column position on a one-based source line."""

    line: int
    column: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("A source position line must be at least 1")
        if self.column < 0:
            raise ValueError("A source position column cannot be negative")


@dataclass(frozen=True)
class SourceSpan:
    """An inclusive-start, exclusive-end range in a Workflow definition."""

    start: SourcePosition
    end: SourcePosition

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("A source span end cannot precede its start")


class ManagedNodeKind(StrEnum):
    """The graph declarations Artio currently manages structurally."""

    SOURCE = "source"
    TRANSFORMATION = "transformation"
    OUTPUT = "output"


@dataclass(frozen=True)
class ManagedNode:
    """A source, Transformation, or Output declaration in a Workflow graph."""

    id: str
    kind: ManagedNodeKind
    span: SourceSpan
    function_name: str | None = None


@dataclass(frozen=True)
class DeclaredEdge:
    """A directed dependency declared between two managed Workflow nodes."""

    source_id: str
    target_id: str


@dataclass(frozen=True)
class WorkflowGraph:
    """The revisioned graph derived from a valid Workflow definition."""

    name: str
    revision: int
    nodes: tuple[ManagedNode, ...]
    edges: tuple[DeclaredEdge, ...]

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("A workflow revision must be at least 1")


class DiagnosticSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Diagnostic:
    """A non-destructive finding about a Workflow definition."""

    code: str
    message: str
    severity: DiagnosticSeverity
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ParseResult:
    """The graph and diagnostics produced by parsing one Workflow definition."""

    workflow: WorkflowGraph | None
    diagnostics: tuple[Diagnostic, ...]
