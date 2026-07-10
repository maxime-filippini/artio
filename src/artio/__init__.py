"""Public declarations used by managed Artio workflow modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class Workflow:
    """A lightweight declaration container for an Artio workflow.

    Its declarations intentionally do not execute data.  They make a newly
    initialized module importable today and establish the stable syntax that the
    future parser and preview worker will inspect.
    """

    name: str
    sources: dict[str, Callable[..., Any]] = field(default_factory=dict)
    transformations: dict[str, Callable[..., Any]] = field(default_factory=dict)
    transformation_inputs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)

    def source(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def declare(function: Callable[..., Any]) -> Callable[..., Any]:
            self.sources[name] = function
            return function

        return declare

    def transform(
        self, name: str, *, inputs: tuple[str, ...]
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def declare(function: Callable[..., Any]) -> Callable[..., Any]:
            self.transformations[name] = function
            self.transformation_inputs[name] = inputs
            return function

        return declare

    def output(self, name: str, transformation: str) -> None:
        self.outputs[name] = transformation


__all__ = ["Workflow"]
