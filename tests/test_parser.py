from __future__ import annotations

import ast

from artio.parser import find_decorated_functions


def test_find_decorated_functions_returns_matching_top_level_functions_in_order() -> None:
    module = ast.parse(
        '''
@workflow.transform("second")
def second(): pass

@workflow.source("orders")
def orders(): pass

@workflow.transform("third")
def third(): pass
'''
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="transform"
    )

    assert [function.name for function in functions] == ["second", "third"]


def test_find_decorated_functions_accepts_a_direct_decorator_reference() -> None:
    module = ast.parse(
        '''
@workflow.source
def orders(): pass
'''
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="source"
    )

    assert [function.name for function in functions] == ["orders"]


def test_find_decorated_functions_excludes_dynamic_and_nested_decorators() -> None:
    module = ast.parse(
        '''
@factory.workflow.transform("dynamic")
def dynamic(): pass

class Example:
    @workflow.transform("nested")
    def nested(self): pass

@workflow.source("orders")
def orders(): pass
'''
    )

    functions = find_decorated_functions(
        module, decorator_module="workflow", decorator_name="transform"
    )

    assert functions == ()
