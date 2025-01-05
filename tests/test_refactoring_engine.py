import ast
import pytest

from refactoring_tool.refactoring_engine import (
    transform_loop_to_comprehension,
    transform_nested_if,
    transform_if_chain_to_dict,
    RefactoringEngine
)

def test_transform_loop_to_comprehension_valid():
    """
    Tests that a valid loop is converted into a list comprehension.
    """
    code_before = """
result = []
for i in range(5):
    result.append(i * 2)
"""
    tree = ast.parse(code_before)
    for_node = tree.body[1]  # The 'for' node

    new_node = transform_loop_to_comprehension(for_node)
    assert isinstance(new_node, ast.Assign), "Should return an Assign node."
    # Check that the Assign node has a ListComp
    assert isinstance(new_node.value, ast.ListComp), "Should transform to a ListComp."

def test_transform_loop_to_comprehension_invalid():
    """
    Tests that an invalid loop raises ValueError.
    """
    code_before = """
result = []
for i in range(5):
    print(i)
"""
    tree = ast.parse(code_before)
    for_node = tree.body[1]

    with pytest.raises(ValueError):
        transform_loop_to_comprehension(for_node)

def test_transform_nested_if_valid():
    """
    Tests merging nested if-statements into a single condition.
    """
    code_before = """
if condition_a:
    if condition_b:
        do_something()
"""
    tree = ast.parse(code_before)
    if_node = tree.body[0]

    new_if = transform_nested_if(if_node)
    assert isinstance(new_if, ast.If), "Should return an If node."
    # Check that the test is a BoolOp with an And
    assert isinstance(new_if.test, ast.BoolOp), "Condition should be BoolOp."
    assert isinstance(new_if.test.op, ast.And), "BoolOp should be 'and'."

def test_transform_if_chain_to_dict_valid():
    """
    Tests converting if-elif-else chain to a dictionary lookup.
    """
    code_before = """
if x == 1:
    action_one()
elif x == 2:
    action_two()
else:
    default_action()
"""
    tree = ast.parse(code_before)
    if_node = tree.body[0]

    result_nodes = transform_if_chain_to_dict(if_node)
    # Should return a list of two statements: Assign (actions dict) and Expr (call).
    assert len(result_nodes) == 2, "Should produce two statements (dict and call)."

def test_refactoring_engine_integration():
    """
    Tests RefactoringEngine high-level methods (refactor_loop, refactor_nested_if, refactor_if_chain).
    """
    engine = RefactoringEngine()

    code = """
result = []
for i in range(5):
    result.append(i)
if condition_a:
    if condition_b:
        nested_action()
if x == 1:
    action_one()
elif x == 2:
    action_two()
else:
    default_action()
"""
    tree = ast.parse(code)

    # Manually walks the tree and apply transformations
    for node in tree.body:
        if isinstance(node, ast.For):
            new_node = engine.refactor_loop(node)
            assert isinstance(new_node, ast.AST)

        if isinstance(node, ast.If):
            new_node = engine.refactor_nested_if(node)
            if isinstance(new_node, ast.If):
                chain_result = engine.refactor_if_chain(new_node)
                # chain_result can be a list of statements or a single If node
                assert isinstance(chain_result, list)