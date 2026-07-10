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


class WorkflowSource:
    def __init__(self, id: str, func: Callable[[], pl.LazyFrame]) -> None:
        self._func = func
        self.id = id


class WorkflowTransformation:
    def __init__(self, id: str, func: Callable[..., pl.LazyFrame]) -> None:
        self._func = func
        self.id = id


type Dependable = WorkflowSource | WorkflowTransformation


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
    sources: dict[str, WorkflowSource] = field(
        default_factory=dict[str, WorkflowSource]
    )
    transformations: dict[str, WorkflowTransformation] = field(
        default_factory=dict[str, WorkflowTransformation]
    )

    outputs: dict[str, WorkflowTransformation] = field(
        default_factory=dict[str, WorkflowTransformation]
    )

    def source(self, id: str):
        # Register a source on the workflow
        def decorator(func: Callable[[], pl.LazyFrame]) -> WorkflowSource:
            _validate_func_annotations(func, self)
            src = WorkflowSource(id=id, func=func)
            self.sources[id] = src
            return src

        return decorator

    def transform(self, id: str):
        # Register a transformation on the workflow
        def declare(func: Callable[..., Any]) -> WorkflowTransformation:
            _validate_func_annotations(func, self)
            transformation = WorkflowTransformation(id=id, func=func)
            self.transformations[id] = transformation
            return transformation

        return declare

    def output(self, name: str, transformation: WorkflowTransformation) -> None:
        self.outputs[name] = transformation
