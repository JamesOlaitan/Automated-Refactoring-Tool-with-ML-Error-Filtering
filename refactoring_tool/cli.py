import sys
import argparse
import os
import ast
import difflib
import logging
from typing import Tuple, List

import astor

from refactoring_tool.code_parser import read_python_file, generate_ast, analyze_file
from refactoring_tool.refactoring_engine import RefactoringEngine

# Imports the ML error filter
try:
    from refactoring_tool.ml_filter import MLErrorFilter
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def main():
    """
    Main function to parse command-line arguments, invoke refactoring,
    and optionally integrate machine learning error filtering.
    """
    parser = argparse.ArgumentParser(description='Automated Refactoring Tool')
    parser.add_argument('input_path', help='Path to the input Python file or directory')
    parser.add_argument('--output', help='Output directory', default='refactored_code')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--use-ml-filter', action='store_true',
                        help='Use the ML model to filter out risky refactorings if available')
    args = parser.parse_args()

    input_path = args.input_path
    output_dir = args.output
    verbose = args.verbose
    use_ml_filter = args.use_ml_filter

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Ensures output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Initializes ML error filter if requested and available
    ml_filter = None
    if use_ml_filter and ML_AVAILABLE:
        ml_filter = MLErrorFilter()
        try:
            ml_filter.load_model()
            logging.info("ML model loaded successfully.")
        except FileNotFoundError:
            logging.warning("No ML model file found. Proceeding without error filtering.")
            ml_filter = None
    elif use_ml_filter and not ML_AVAILABLE:
        logging.warning("ML filter requested but not installed/importable. Proceeding without it.")

    # Processes input path
    if os.path.isfile(input_path):
        process_file(input_path, output_dir, verbose, ml_filter)
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, output_dir, verbose, ml_filter)
    else:
        print(f"The path {input_path} is not a valid file or directory.")
        sys.exit(1)


def process_file(file_path: str, output_dir: str, verbose: bool, ml_filter: 'MLErrorFilter' = None):
    """
    Processes a single Python file:
    - Analyzes for refactoring opportunities.
    - Applies refactorings if applicable.
    - Optionally checks for error risk with an ML model.
    - Generates refactored code and produces a diff.
    - Writes the refactored file to the output directory if accepted,
      otherwise writes the original file.

    :param file_path: Path to the Python file to be processed.
    :type file_path: str
    :param output_dir: Directory where refactored code will be written.
    :type output_dir: str
    :param verbose: Flag indicating verbosity of output.
    :type verbose: bool
    :param ml_filter: Instance of MLErrorFilter or None if unused.
    :type ml_filter: MLErrorFilter or None
    """
    loop_issues, nested_if_issues, if_chain_issues = analyze_file(file_path)
    total_issues = len(loop_issues) + len(nested_if_issues) + len(if_chain_issues)

    if total_issues == 0:
        if verbose:
            print(f"No issues found in {file_path}.")
        # Writes the original file to output directory for consistency
        write_original_file(file_path, output_dir)
        return

    if verbose:
        print(f"Issues in {file_path}:")
        for issue in loop_issues:
            print(f"Line {issue['line']}: {issue['message']}")
        for issue in nested_if_issues:
            print(f"Line {issue['line']}: {issue['message']}")
        for issue in if_chain_issues:
            print(f"Line {issue['line']}: {issue['message']}")

    refactored_code = apply_refactorings(file_path)
    if refactored_code is None:
        write_original_file(file_path, output_dir)
        return

    # If ML filter is available, checks error probability
    if ml_filter is not None:
        original_code = read_python_file(file_path)
        error_probability = ml_filter.predict_refactoring_error(original_code, refactored_code)
        error_threshold = 0.3  # this threshold can be adjusted as needed

        if error_probability > error_threshold:
            logging.warning(f"Refactoring on {file_path} deemed risky (prob={error_probability:.2f}). Skipping.")
            write_original_file(file_path, output_dir)
            return
        else:
            logging.debug(f"Refactoring on {file_path} accepted (prob={error_probability:.2f}).")

    # Generates diff
    original_code_lines = read_python_file(file_path).splitlines(keepends=True)
    refactored_lines = refactored_code.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_code_lines,
        refactored_lines,
        fromfile=file_path,
        tofile=os.path.join(output_dir, os.path.basename(file_path))
    )
    diff_text = ''.join(diff)

    if diff_text.strip() and verbose:
        print("Refactoring Diff:")
        print(diff_text)

    # Writes the refactored code to the output directory
    write_refactored_file(file_path, output_dir, refactored_code)


def apply_refactorings(file_path: str) -> str:
    """
    Applies refactorings to the given file and returns the refactored code as a string.

    Steps:
    - Parse the file into an AST.
    - Identify nodes that can be refactored (loops, nested ifs, if-elif-else chains).
    - Apply transformations using RefactoringEngine.
    - Convert AST back to code using astor.to_source().

    :param file_path: Path to the Python file.
    :type file_path: str
    :return: Refactored code or None if refactoring fails.
    :rtype: str or None
    """
    try:
        original_code = read_python_file(file_path)
        tree = generate_ast(original_code)
    except Exception as e:
        logging.warning(f"Could not parse {file_path}: {e}")
        return None

    engine = RefactoringEngine()
    transformed_tree = refactor_ast(tree, engine)

    try:
        refactored_code = astor.to_source(transformed_tree)
        return refactored_code
    except Exception as e:
        logging.warning(f"Error converting AST back to code for {file_path}: {e}")
        return None


def refactor_ast(tree: ast.AST, engine: 'RefactoringEngine') -> ast.AST:
    """
    Traverses the AST and applies transformations to detected patterns:
    - For-loops that can be converted to comprehensions.
    - Nested if-statements that can be merged.
    - If-elif-else chains that can be replaced with dictionary lookups.

    :param tree: The AST of the code.
    :type tree: ast.AST
    :param engine: An instance of RefactoringEngine.
    :type engine: RefactoringEngine
    :return: The transformed AST.
    :rtype: ast.AST
    """
    class RefactoringVisitor(ast.NodeTransformer):
        def visit_For(self, node: ast.For) -> ast.AST:
            node = self.generic_visit(node)
            return engine.refactor_loop(node)

        def visit_If(self, node: ast.If) -> ast.AST:
            node = self.generic_visit(node)
            node = engine.refactor_nested_if(node) if isinstance(node, ast.If) else node
            if isinstance(node, ast.If):
                result = engine.refactor_if_chain(node)
                if len(result) == 1 and isinstance(result[0], ast.If):
                    return result[0]
                elif len(result) == 2:
                    # If chain was successfully transformed into two statements
                    # We'll keep the original node if we can't properly insert two statements in place.
                    return node
                else:
                    return node
            return node

    visitor = RefactoringVisitor()
    transformed_tree = visitor.visit(tree)
    ast.fix_missing_locations(transformed_tree)
    return transformed_tree


def write_original_file(file_path: str, output_dir: str):
    """
    Copies the original file into the output directory without changes.

    :param file_path: Path to the original file.
    :type file_path: str
    :param output_dir: Directory to write the file.
    :type output_dir: str
    """
    code = read_python_file(file_path)
    write_path = os.path.join(output_dir, os.path.basename(file_path))
    with open(write_path, 'w', encoding='utf-8') as f:
        f.write(code)


def write_refactored_file(file_path: str, output_dir: str, refactored_code: str):
    """
    Writes the refactored code to the output directory.

    :param file_path: Path to the original file.
    :type file_path: str
    :param output_dir: Directory to write the refactored code.
    :type output_dir: str
    :param refactored_code: The transformed code.
    :type refactored_code: str
    """
    write_path = os.path.join(output_dir, os.path.basename(file_path))
    with open(write_path, 'w', encoding='utf-8') as f:
        f.write(refactored_code)


if __name__ == "__main__":
    main()