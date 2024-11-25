import ast
from typing import List, Any, Tuple

def read_python_file(file_path: str) -> str:
    """
    Reads Python code from a file.

    :param file_path: Path to the Python (.py) file.
    :return: String containing the Python code.
    :raises FileNotFoundError: If the file does not exist.
    :raises IOError: If the file cannot be read.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()
        return code
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    except IOError as e:
        raise IOError(f"An error occurred while reading the file {file_path}: {e}")

def generate_ast(code: str) -> ast.AST:
    """
    Generates an Abstract Syntax Tree (AST) from Python code.

    :param code: String containing Python code.
    :return: AST object representing the code structure.
    :raises SyntaxError: If the code contains syntax errors.
    """
    try:
        tree = ast.parse(code)
        return tree
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in code: {e}")

class BaseDetector(ast.NodeVisitor):
    """
    Base class for AST node visitors for pattern detection.
    """

    def __init__(self):
        self.issues = []

    def report_issue(self, node: ast.AST, message: str):
        """
        Records an issue found during AST traversal.

        :param node: The AST node where the issue was found.
        :param message: Description of the issue.
        """
        issue = {
            'line': node.lineno,
            'col': node.col_offset,
            'message': message,
            'node': node
        }
        self.issues.append(issue)

class ForLoopDetector(BaseDetector):
    """
    Detects for-loops that can be converted into list comprehensions or generator expressions.
    """

    def visit_For(self, node: ast.For):
        """
        Visits all For nodes in the AST.

        :param node: AST For node.
        """
        if self.is_append_loop(node):
            self.report_issue(
                node,
                "For-loop can be converted to a list comprehension."
            )
        self.generic_visit(node)

    @staticmethod
    def is_append_loop(node: ast.For) -> bool:
        """
        Determines if a for-loop is an append loop.

        :param node: AST For node.
        :return: True if it is an append loop, False otherwise.
        """
        # Check if the body has a single expression that appends to a list
        if len(node.body) != 1:
            return False
        stmt = node.body[0]
        # Handle both Expr and Assign nodes
        if isinstance(stmt, (ast.Expr, ast.Assign)):
            if isinstance(stmt, ast.Assign):
                # Handle cases like result += [item * 2]
                return True
            expr = stmt.value
            if isinstance(expr, ast.Call):
                if isinstance(expr.func, ast.Attribute):
                    if expr.func.attr == 'append':
                        return True
        return False

class NestedIfDetector(BaseDetector):
    """
    Detects nested if-statements that can be merged.
    """

    def visit_If(self, node: ast.If):
        """
        Visits all If nodes in the AST.

        :param node: AST If node.
        """
        if self.is_nested_if(node):
            self.report_issue(
                node,
                "Nested if-statements can be merged."
            )
        self.generic_visit(node)

    @staticmethod
    def is_nested_if(node: ast.If) -> bool:
        """
        Determines if an if-statement contains a nested if-statement that can be merged.

        :param node: AST If node.
        :return: True if nested if-statements can be merged, False otherwise.
        """
        if len(node.body) == 1 and isinstance(node.body[0], ast.If):
            return True
        return False

class IfElseChainDetector(BaseDetector):
    """
    Detects if-elif-else chains that can be replaced with dictionary lookups.
    """

    def visit_If(self, node: ast.If):
        """
        Visits all If nodes in the AST.

        :param node: AST If node.
        """
        chain_length = self.get_if_chain_length(node)
        if chain_length >= 3:
            self.report_issue(
                node,
                "If-elif-else chain can be replaced with a dictionary."
            )
        self.generic_visit(node)

    def get_if_chain_length(self, node: ast.If) -> int:
        """
        Calculates the length of an if-elif-else chain.

        :param node: AST If node.
        :return: Length of the if-elif-else chain.
        """
        length = 1
        current_node = node.orelse
        while current_node:
            if len(current_node) == 1 and isinstance(current_node[0], ast.If):
                length += 1
                current_node = current_node[0].orelse
            else:
                break
        return length

def analyze_file(file_path: str) -> Tuple[List[Any], List[Any], List[Any]]:
    """
    Analyzes a Python file for specific refactoring opportunities.

    :param file_path: Path to the Python file.
    :return: Tuple containing lists of issues detected by each detector.
    """
    try:
        code = read_python_file(file_path)
        tree = generate_ast(code)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return [], [], []

    # Initialize detectors
    loop_detector = ForLoopDetector()
    nested_if_detector = NestedIfDetector()
    if_chain_detector = IfElseChainDetector()

    # Visit the AST
    loop_detector.visit(tree)
    nested_if_detector.visit(tree)
    if_chain_detector.visit(tree)

    return (
        loop_detector.issues,
        nested_if_detector.issues,
        if_chain_detector.issues
    )