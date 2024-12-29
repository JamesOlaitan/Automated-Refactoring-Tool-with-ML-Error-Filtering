# Automated Refactoring Tool with ML Error Filtering

An automated refactoring tool that identifies specific code patterns (for loops and nested if-else statements) in Python codebases, refactors them to more efficient or readable forms, and uses machine learning (via TensorFlow) to predict and filter out refactorings that may introduce errors.


## Project Structure

- **refactoring_tool/**: Contains the main application code.
  - **__init__.py**: Makes `refactoring_tool` a Python package.
  - **cli.py**: Command-line interface for the tool.
  - **code_parser.py**: Code parsing and pattern detection.
  - **refactoring_engine.py**: Applies specific AST-based refactoring transformations.
  - **ml_filter.py**: Machine learning component to predict error likelihood in refactorings.
- **tests/**: Unit tests for code validation.
  - **__init__.py**
  - **test_parser.py**: Tests for `code_parser.py`.
  - **sample_code/**: Sample Python files for testing.
    - **sample_loop.py** (inefficient loops)
    - **sample_nested_if.py** (nested if-statements)
    - **sample_if_chain.py** (if-elif-else chains)
    - **sample_no_issues.py** (no issues detected)
- **setup.py**: Installation and packaging configuration.
- **MANIFEST.in**: Specifies additional files to include in the package.
- **README.md**: Project documentation.
- **LICENSE**: Project license.
- **data/** (optional): Directory to store training data (user-provided CSV).
- **models/** (optional): Directory to store the trained ML model file (`model.pkl`).


## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JamesOlaitan/Automated-Refactoring-Tool-with-ML-Error-Filtering.git
   cd Automated-Refactoring-Tool-with-ML-Error-Filtering
   
2. **Create and Activate a Virtual Environment (Optional but Recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   
3. **Install the Package and Dependencies**

   ```bash
   pip install -e .

   *This installs the tool in editable mode. Additionally, ensure required dependencies like radon, pandas, and scikit-learn are installed:*

   ```bash
   pip install radon pandas scikit-learn
   ```

## Usage

**Analyzing and Reporting Issues**

Run the CLI to detect refactoring opportunities:

   ```bash
   refactor path/to/your_script.py

- The tool will print out detected issues (inefficient loops, nested ifs, and if-elif-else chains).
- If run on a directory, it analyzes all .py files within it.
- Use -v for verbose output:

   ```bash
   refactor path/to/your_script.py -v


## Using the ML Error Filter

**Overview**

The ML component (ml_filter.py) predicts whether a given refactoring might introduce errors. This requires:
- A labeled dataset of refactorings (both successful and failed)
- Training a model on this dataset
- Using the trained model to filter out risky refactorings before applying them

**Logging Failed Refactorings**

When you encounter a refactoring that doesn’t work out (e.g., the code breaks tests, runtime errors), log it into a CSV file to build a dataset. Your CSV file (data/dataset.csv) should have the following columns:

- code_before: The exact code snippet before the refactoring.
- code_after: The refactored code snippet.
- error_introduced: 1 if the refactoring introduced an error, 0 otherwise.

**Example CSV Row:**

   ```bash
   code_before,code_after,error_introduced
"result = []\nfor i in items:\n    result.append(i*2)","result = [i*2 for i in items]",0

If you encountered a failed refactoring:

   ```bash
   code_before,code_after,error_introduced
"integer = 30\nif integer % 2 == 0:\n    if integer % 3 == 0:\n        print('divisible')","integer = 30\nif (integer % 2 == 0 and integer % 3 == 0):\n    print('divisible')",1

Over time, accumulate multiple such examples. The more data you provide, the better the model can learn.


## Training the Model

Once you have a sufficient dataset:

   ```bash
   python refactoring_tool/ml_filter.py train --data data/dataset.csv

This command:
- Loads the dataset.
- Extracts features (complexity, length, nesting, variable usage).
- Trains a Random Forest model with hyperparameter tuning.
- Saves the best model as models/model.pkl.

## Using the Model to Predict Error Likelihood

After training, you can predict error probability for a given refactoring:


   ```bash
   python refactoring_tool/ml_filter.py predict --before path/to/code_before.py --after path/to/code_after.py

   This loads the model and prints the predicted probability of error introduction. For example:
   ```bash
   Predicted error probability: 0.23

You can integrate this prediction step into your refactoring pipeline:
- If the probability is high, skip the refactoring.
- If low, proceed.