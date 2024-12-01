# Automated Refactoring Tool with ML Error Filtering

An automated refactoring tool that identifies specific code patterns (for loops and nested if-else statements) in Python codebases, refactors them to more efficient or readable forms, and uses machine learning (via TensorFlow) to predict and filter out refactorings that may introduce errors.

## Project Structure

- **refactoring_tool/**: Contains the main application code.
  - **__init__.py**: Makes `refactoring_tool` a Python package.
  - **cli.py**: Command-line interface for the tool.
  - **code_parser.py**: Code parsing and pattern detection.
- **tests/**: Unit tests for code validation.
  - **__init__.py**
  - **test_parser.py**: Tests for `code_parser.py`.
  - **sample_code/**: Sample Python files for testing.
    - **sample_loop.py**
    - **sample_nested_if.py**
    - **sample_if_chain.py**
    - **sample_no_issues.py**
- **setup.py**: Installation and packaging configuration.
- **MANIFEST.in**: Specifies additional files to include in the package.
- **README.md**: Project documentation.
- **LICENSE**: Project license.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JamesOlaitan/Automated-Refactoring-Tool-with-ML-Error-Filtering.git
   cd Automated-Refactoring-Tool-with-ML-Error-Filtering
   
2. **Create and Activate a Virtual Environment (Optional but Recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   
