import sys
import argparse
import os
from parser import analyze_file

def main():
    """
    Main function to parse command-line arguments and invoke the analyzer.
    """
    parser = argparse.ArgumentParser(description='Automated Refactoring Tool')
    parser.add_argument('input_path', help='Path to the input Python file or directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    input_path = args.input_path
    verbose = args.verbose

    # Analyze the input path
    if os.path.isfile(input_path):
        analyze_and_report(input_path, verbose)
    elif os.path.isdir(input_path):
        # Analyze all .py files in the directory
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    analyze_and_report(file_path, verbose)
    else:
        print(f"The path {input_path} is not a valid file or directory.")
        sys.exit(1)

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