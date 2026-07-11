"""Public declarations used by managed Artio workflow modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from inspect import signature
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin
from typing import get_type_hints

import polars as pl

from artio.exceptions import ArgumentDependsOnNonExistentComponentError
from artio.exceptions import ArgumentMissingSourceInformation
from artio.exceptions import MissingTypeHintInWorkflowComponentError
from artio.exceptions import NonAnnotatedArgumentInWorkflowComponentError


def _validate_func_annotations(func: Callable[..., Any], workflow: Workflow):
    params = signature(func).parameters
    type_hints = get_type_hints(func, include_extras=True)

    for k, _ in params.items():
        if k not in type_hints:
            raise MissingTypeHintInWorkflowComponentError

        type_hint = type_hints[k]

        if get_origin(type_hint) != Annotated:
            raise NonAnnotatedArgumentInWorkflowComponentError(k)

        args = get_args(type_hint)

        found = False

        for arg in args:
            if not isinstance(arg, Depends):
                continue

            source_id = arg.dep.id
            found = True

            if (
                source_id not in workflow.sources
                and source_id not in workflow.transformations
            ):
                raise ArgumentDependsOnNonExistentComponentError

            break

        if not found:
            raise ArgumentMissingSourceInformation


class Source:
    def __init__(self, id: str, func: Callable[[], pl.LazyFrame]) -> None:
        self._func = func
        self.id = id


class Transformation:
    def __init__(self, id: str, func: Callable[..., pl.LazyFrame]) -> None:
        self._func = func
        self.id = id


class Fixture:
    def __init__(self, id: str, func: Callable[[], pl.LazyFrame]):
        self.id = id
        self._func = func


class DecisionTree[**P]:
    def __init__(self, id: str, func: Callable[P, pl.Expr]):
        self.id = id
        self._func = func


type Dependable = Source | Transformation


class Depends:
    def __init__(self, dep: Dependable) -> None:
        self.dep = dep


@dataclass
class Workflow:
    """A lightweight declaration container for an Artio workflow.

    Its declarations intentionally do not execute data.  They make a newly
    initialized module importable today and establish the stable syntax that the
    future parser and preview worker will inspect.
    """

    name: str
    fixtures: dict[str, Fixture] = field(default_factory=dict[str, Fixture])
    decision_trees: dict[str, DecisionTree] = field(
        default_factory=dict[str, DecisionTree]
    )
    sources: dict[str, Source] = field(default_factory=dict[str, Source])
    transformations: dict[str, Transformation] = field(
        default_factory=dict[str, Transformation]
    )

    outputs: dict[str, Transformation] = field(
        default_factory=dict[str, Transformation]
    )

    def source(self, id: str):
        # Register a source on the workflow
        def decorator(func: Callable[[], pl.LazyFrame]) -> Source:
            _validate_func_annotations(func, self)
            src = Source(id=id, func=func)
            self.sources[id] = src
            return src

        return decorator

    def fixture(self, id: str):
        """Register reusable local sample data without executing it."""

        def decorator(func: Callable[[], pl.LazyFrame]) -> Fixture:
            fixture = Fixture(id=id, func=func)
            self.fixtures[id] = fixture
            return fixture

        return decorator

    def decision_tree[**P](
        self, id: str
    ) -> Callable[[Callable[P, pl.Expr]], DecisionTree[P]]:
        """Register a reusable Polars expression without executing it."""

        def decorator(func: Callable[P, pl.Expr]) -> DecisionTree[P]:
            decision_tree = DecisionTree(id=id, func=func)
            self.decision_trees[id] = decision_tree
            return decision_tree

        return decorator

    def transform(self, id: str):
        # Register a transformation on the workflow
        def declare(func: Callable[..., Any]) -> Transformation:
            _validate_func_annotations(func, self)
            transformation = Transformation(id=id, func=func)
            self.transformations[id] = transformation
            return transformation

        return declare

    def output(self, name: str, transformation: Transformation) -> None:
        self.outputs[name] = transformation
