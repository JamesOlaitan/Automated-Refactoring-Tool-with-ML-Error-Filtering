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


def main():
    """
    Main function to parse command-line arguments and invoke the refactoring process.
    """
    parser = argparse.ArgumentParser(description='Automated Refactoring Tool')
    parser.add_argument('input_path', help='Path to the input Python file or directory')
    parser.add_argument('--output', help='Output directory', default='refactored_code')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    input_path = args.input_path
    output_dir = args.output
    verbose = args.verbose

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Ensures output directory exists
    os.makedirs(output_dir, exist_ok=True)

    if os.path.isfile(input_path):
        process_file(input_path, output_dir, verbose)
    elif os.path.isdir(input_path):
        # Processes all .py files in the directory
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, output_dir, verbose)
    else:
        print(f"The path {input_path} is not a valid file or directory.")
        sys.exit(1)


def process_file(file_path: str, output_dir: str, verbose: bool):
    """
    Processes a single Python file:
    - Analyzes for refactoring opportunities.
    - Applies refactorings if applicable.
    - Generates refactored code and produces diff.
    - Writes the refactored file to the output directory.

    :param file_path: Path to the Python file to be processed.
    :type file_path: str
    :param output_dir: Directory where refactored code will be written.
    :type output_dir: str
    :param verbose: Flag indicating verbosity of output.
    :type verbose: bool
    """
    loop_issues, nested_if_issues, if_chain_issues = analyze_file(file_path)

    total_issues = len(loop_issues) + len(nested_if_issues) + len(if_chain_issues)
    if total_issues == 0:
        if verbose:
            print(f"No issues found in {file_path}.")
        # Still writes the original file to output directory for consistency
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
        # If refactoring couldn't proceed, copies original file
        write_original_file(file_path, output_dir)
        return

    # Generates a diff
    original_code = read_python_file(file_path).splitlines(keepends=True)
    refactored_lines = refactored_code.splitlines(keepends=True)
    diff = difflib.unified_diff(original_code, refactored_lines,
                                fromfile=file_path,
                                tofile=os.path.join(output_dir, os.path.basename(file_path)))
    
    diff_text = ''.join(diff)

    if diff_text.strip():
        if verbose:
            print("Refactoring Diff:")
            print(diff_text)
    else:
        if verbose:
            print("No changes were made after refactoring.")

    # Writes the refactored code to the output directory
    write_refactored_file(file_path, output_dir, refactored_code)



def apply_refactorings(file_path: str) -> str:
    """
    Applies refactorings to the given file and returns the refactored code as a string.

    Steps:
    - Parse the file into AST.
    - Identify nodes that can be refactored (loops, nested ifs, if chains).
    - Apply transformations using RefactoringEngine.
    - Convert AST back to code using astor.

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
    Traverses the AST and applies transformations to detected patterns.

    This function:
    - Finds loops suitable for refactoring.
    - Finds nested if-statements and merges them.
    - Finds if-elif-else chains and converts them to dictionary lookups.

    :param tree: The AST of the code.
    :type tree: ast.AST
    :param engine: An instance of RefactoringEngine.
    :type engine: RefactoringEngine
    :return: The transformed AST.
    :rtype: ast.AST
    """


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


def analyze_and_report(file_path: str, verbose: bool = False):
    """
    Analyzes a single file and reports detected issues.

    :param file_path: Path to the Python file.
    :param verbose: Flag to enable verbose output.
    """
    loop_issues, nested_if_issues, if_chain_issues = analyze_file(file_path)

    total_issues = len(loop_issues) + len(nested_if_issues) + len(if_chain_issues)

    if total_issues == 0 and verbose:
        print(f"No issues found in {file_path}.")
        return
    elif total_issues == 0:
        return

    print(f"Issues in {file_path}:")

    for issue in loop_issues:
        print(f"Line {issue['line']}: {issue['message']}")

    for issue in nested_if_issues:
        print(f"Line {issue['line']}: {issue['message']}")

    for issue in if_chain_issues:
        print(f"Line {issue['line']}: {issue['message']}")

if __name__ == "__main__":
    main()
