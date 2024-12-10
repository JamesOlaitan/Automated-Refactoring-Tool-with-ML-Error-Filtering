import ast
import logging

# Configures logging for refactoring actions
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def transform_loop_to_comprehension(for_node: ast.For) -> ast.AST:
    """
    Transforms a for-loop that appends elements to a list into a list comprehension assignment.

    Expected pattern:
    
    .. code-block:: python

        result = []
        for item in iterable:
            result.append(expression)

    Transformed to:
    
    .. code-block:: python

        result = [expression for item in iterable]

    :param for_node: The AST For node representing the loop.
    :type for_node: ast.For
    :return: An AST node representing the transformed code.
    :rtype: ast.AST
    :raises ValueError: If the provided for_node does not match the expected pattern.
    """
    if len(for_node.body) != 1:
        raise ValueError("The for-loop does not match the expected pattern (single statement in body).")

    stmt = for_node.body[0]

    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        raise ValueError("The for-loop body does not contain an append call.")

    call_expr = stmt.value
    if (not isinstance(call_expr.func, ast.Attribute) or
        call_expr.func.attr != 'append' or
        len(call_expr.args) != 1):
        raise ValueError("The for-loop body does not contain a valid append call.")

    append_func = call_expr.func
    if not isinstance(append_func.value, ast.Name):
        raise ValueError("The append call is not on a simple variable.")

    result_var_name = append_func.value.id
    appended_expr = call_expr.args[0]

    list_comp = ast.ListComp(
        elt=appended_expr,
        generators=[ast.comprehension(
            target=for_node.target,
            iter=for_node.iter,
            ifs=[],
            is_async=0
        )]
    )

    assign_node = ast.Assign(
        targets=[ast.Name(id=result_var_name, ctx=ast.Store())],
        value=list_comp
    )

    ast.fix_missing_locations(assign_node)
    return assign_node

def transform_nested_if(if_node: ast.If) -> ast.AST:
    """
    Transforms nested if-statements into a single if-statement with a combined condition.

    Expected pattern:

    .. code-block:: python

        if condition_a:
            if condition_b:
                body

    Transformed to:

    .. code-block:: python

        if (condition_a and condition_b):
            body

    :param if_node: The AST If node at the top level.
    :type if_node: ast.If
    :return: An AST node representing the transformed if-statement.
    :rtype: ast.AST
    :raises ValueError: If the pattern does not match a nested if scenario.
    """
    if len(if_node.body) != 1 or not isinstance(if_node.body[0], ast.If):
        raise ValueError("The if-node does not contain a nested if-statement as a single body element.")

    inner_if = if_node.body[0]

    combined_test = ast.BoolOp(
        op=ast.And(),
        values=[if_node.test, inner_if.test]
    )

    new_if = ast.If(
        test=combined_test,
        body=inner_if.body,
        orelse=if_node.orelse
    )

    ast.fix_missing_locations(new_if)
    return new_if

def transform_if_chain_to_dict(if_node: ast.If) -> ast.AST:
    """
    Transforms an if-elif-else chain checking equality against a single variable into a dictionary lookup.

    Expected pattern:
    
    .. code-block:: python

        if x == 1:
            action_one()
        elif x == 2:
            action_two()
        elif x == 3:
            action_three()
        else:
            default_action()

    Transformed to:

    .. code-block:: python

        actions = {
            1: lambda: action_one(),
            2: lambda: action_two(),
            3: lambda: action_three()
        }
        actions.get(x, lambda: default_action())()

    :param if_node: The AST If node representing the if-elif-else chain.
    :type if_node: ast.If
    :return: An AST node list representing the dictionary definition and call (two statements).
    :rtype: list[ast.stmt]
    :raises ValueError: If the chain does not match the expected pattern.
    """
    # Gathers conditions and bodies
    chain = []
    current = if_node
    variable_name = None

    while current:
        # Checks if condition is binary op of form: var == constant
        if not isinstance(current.test, ast.Compare) or len(current.test.ops) != 1:
            raise ValueError("If chain conditions are not simple comparisons.")

        if not isinstance(current.test.ops[0], ast.Eq):
            raise ValueError("If chain conditions must be equality checks.")

        left = current.test.left
        if variable_name is None:
            if not isinstance(left, ast.Name):
                raise ValueError("If chain conditions must compare a variable to a constant.")
            variable_name = left.id
        else:
            # Ensures all conditions check the same variable
            if not (isinstance(left, ast.Name) and left.id == variable_name):
                raise ValueError("If chain conditions must compare the same variable.")

        # Expects the right side to be a constant
        if not (len(current.test.comparators) == 1 and isinstance(current.test.comparators[0], ast.Constant)):
            raise ValueError("If chain conditions must compare against constants.")

        condition_value = current.test.comparators[0].value

        # Action body must be a list of statements
        action_body = current.body

        chain.append((condition_value, action_body))

        # Moves to the elif part by looking at orelse
        # If there's an orelse that contains a single If, it's an elif
        if (len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If)):
            current = current.orelse[0]
        else:
            # no more elifs
            else_body = current.orelse
            if else_body:
                chain.append(('__else__', else_body))
            current = None

    # Constructs the actions dictionary
    # actions = {
    #   1: lambda: action_one(),
    #   2: lambda: action_two(),
    #   ...
    # }
    dict_keys = []
    dict_values = []
    default_body = None

    for (cond_val, body) in chain:
        if cond_val == '__else__':
            # This is the default action
            default_body = body
        else:
            # Wraps each body in a lambda: lambda: <body>
            # Body is a list of statements
            lambda_func = ast.Lambda(
                args=ast.arguments(
                    posonlyargs=[],
                    args=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[]
                ),
                body=wrap_body_in_expression(body)
            )
            dict_keys.append(ast.Constant(value=cond_val))
            dict_values.append(lambda_func)

    actions_dict = ast.Dict(keys=dict_keys, values=dict_values)

    # Assigns to a variable:
    # actions = {...}
    actions_assign = ast.Assign(
        targets=[ast.Name(id="actions", ctx=ast.Store())],
        value=actions_dict
    )

    # Builds call: actions.get(x, lambda: default_action())()
    if default_body:
        default_lambda = ast.Lambda(
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=wrap_body_in_expression(default_body)
        )
        get_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="actions", ctx=ast.Load()),
                attr="get",
                ctx=ast.Load()
            ),
            args=[ast.Name(id=variable_name, ctx=ast.Load()), default_lambda],
            keywords=[]
        )
    else:
        # No default action
        get_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="actions", ctx=ast.Load()),
                attr="get",
                ctx=ast.Load()
            ),
            args=[ast.Name(id=variable_name, ctx=ast.Load())],
            keywords=[]
        )

    final_call = ast.Call(
        func=get_call,
        args=[],
        keywords=[]
    )

    final_expr = ast.Expr(value=final_call)

    ast.fix_missing_locations(actions_assign)
    ast.fix_missing_locations(final_expr)

    return [actions_assign, final_expr]

def wrap_body_in_expression(body):
    """
    Wraps a body (list of statements) into a single expression node if possible.
    If the body is multiple statements, return the last statement as an expression (or a tuple).

    For this transformation, we assume that the body ends with a statement that can be returned as an expression.
    If not, wrap it in a tuple or return a constant. For simplicity, we assume the last statement can be expressionized.
    
    :param body: List of AST statements.
    :type body: list[ast.stmt]
    :return: An AST expression node representing the body.
    :rtype: ast.expr
    """
    # If there's a single statement and it's an Expr, return its value.
    if len(body) == 1 and isinstance(body[0], ast.Expr):
        return body[0].value

    # Otherwise, just returns a Constant(None)
    return ast.Constant(value=None)

class RefactoringEngine:
    """
    The RefactoringEngine class applies various code transformations to an AST.

    This includes:
    - Converting inefficient loops to list comprehensions.
    - Merging nested if-statements into a single if with a combined condition.
    - Replacing if-elif-else chains with dictionary lookups.

    The engine ensures that variable scopes and semantics are preserved to maintain
    the original code's functionality. If a refactoring pattern cannot be applied,
    it will log a warning and leave the code as-is.
    """

    def refactor_loop(self, for_node: ast.For) -> ast.AST:
        """
        Attempts to refactor a given for-loop node into a list comprehension if it matches the known pattern.

        :param for_node: The AST For node to be refactored.
        :type for_node: ast.For
        :return: The refactored AST node if applicable, otherwise the original node.
        :rtype: ast.AST
        """
        try:
            return transform_loop_to_comprehension(for_node)
        except ValueError as e:
            # Logs a warning and returns the original node
            lineno = getattr(for_node, 'lineno', 'unknown')
            logging.warning(f"Skipped refactoring at line {lineno}: {e}")
            return for_node

    def refactor_nested_if(self, if_node: ast.If) -> ast.AST:
        """
        Attempts to refactor nested if-statements into a single if-statement with a combined condition.

        :param if_node: The AST If node to be refactored.
        :type if_node: ast.If
        :return: The refactored AST node if applicable, otherwise the original node.
        :rtype: ast.AST
        """
        try:
            return transform_nested_if(if_node)
        except ValueError as e:
            lineno = getattr(if_node, 'lineno', 'unknown')
            logging.warning(f"Skipped refactoring at line {lineno}: {e}")
            return if_node

    def refactor_if_chain(self, if_node: ast.If) -> list[ast.stmt]:
        """
        Attempts to refactor if-elif-else chains into a dictionary-based lookup.

        :param if_node: The AST If node representing the start of the if-elif-else chain.
        :type if_node: ast.If
        :return: A list of AST statements representing the refactored code if applicable, otherwise the original node in a list.
        :rtype: list[ast.stmt]
        """
        try:
            return transform_if_chain_to_dict(if_node)
        except ValueError as e:
            lineno = getattr(if_node, 'lineno', 'unknown')
            logging.warning(f"Skipped refactoring at line {lineno}: {e}")
            # Returns the original node as a list to maintain consistency
            return [if_node]