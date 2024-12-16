import os
import logging
import pickle
from typing import Any, Dict, List, Tuple
import ast

import numpy as np
import pandas as pd
from radon.complexity import cc_visit
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class MLErrorFilter:
    """
    The MLErrorFilter class contains functionality for training,
    evaluating, and using a machine learning model to predict whether
    a given refactoring introduces errors.

    It includes methods to:
    - Load and prepare data (before/after code snippets with labels).
    - Extract features using radon for complexity and heuristics for nesting depth and variable usage.
    - Train and tune the ML model.
    - Predict error likelihood for new code transformations.
    """

    def __init__(self, model_path: str = "models/model.pkl"):
        """
        Initializes the MLErrorFilter class.

        :param model_path: Path to the trained model file.
        :type model_path: str
        """
        self.model_path = model_path
        self.model = None

    def load_data(self, data_path: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Loads the dataset of before/after code snippets and their labels.

        Expected CSV format:
        Columns: code_before, code_after, error_introduced (0 or 1)

        :param data_path: Path to the CSV file containing the dataset.
        :type data_path: str
        :return: Features DataFrame (X) and labels Series (y)
        :rtype: Tuple[pd.DataFrame, pd.Series]
        """
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found at {data_path}")

        data = pd.read_csv(data_path)
        if not {'code_before', 'code_after', 'error_introduced'}.issubset(data.columns):
            raise ValueError("Dataset must contain 'code_before', 'code_after', and 'error_introduced' columns.")

        feature_rows = []
        labels = data['error_introduced']

        for _, row in data.iterrows():
            feats = self.extract_features(row['code_before'], row['code_after'])
            feature_rows.append(feats)

        X = pd.DataFrame(feature_rows)
        y = labels
        return X, y

    def extract_features(self, code_before: str, code_after: str) -> Dict[str, Any]:
        """
        Extracts features from code snippets before and after refactoring.

        This function computes various metrics:
        - Cyclomatic complexity using radon
        - Code length (number of lines)
        - Nesting depth (heuristic using AST)
        - Variable usage patterns (basic heuristic counting variable names)

        :param code_before: The code snippet before refactoring.
        :type code_before: str
        :param code_after: The code snippet after refactoring.
        :type code_after: str
        :return: A dictionary of extracted features.
        :rtype: Dict[str, Any]
        """
        complexity_before = self.compute_cyclomatic_complexity(code_before)
        complexity_after = self.compute_cyclomatic_complexity(code_after)

        length_before = self.compute_code_length(code_before)
        length_after = self.compute_code_length(code_after)

        nesting_before = self.estimate_nesting_depth(code_before)
        nesting_after = self.estimate_nesting_depth(code_after)

        var_usage_diff = self.estimate_variable_usage_difference(code_before, code_after)

        features = {
            'complexity_before': complexity_before,
            'complexity_after': complexity_after,
            'complexity_change': complexity_after - complexity_before,
            'length_before': length_before,
            'length_after': length_after,
            'length_change': length_after - length_before,
            'nesting_before': nesting_before,
            'nesting_after': nesting_after,
            'nesting_change': nesting_after - nesting_before,
            'variable_usage_diff': var_usage_diff,
        }

        return features

    def compute_cyclomatic_complexity(self, code: str) -> float:
        """
        Computes cyclomatic complexity using radon.

        :param code: The code snippet.
        :type code: str
        :return: Average cyclomatic complexity of all functions/classes in the snippet.
        :rtype: float
        """
        try:
            blocks = cc_visit(code)
            if not blocks:
                return 0.0
            complexities = [block.complexity for block in blocks]
            return float(np.mean(complexities))
        except Exception:
            # If parsing fails or code is empty
            return 0.0

    def compute_code_length(self, code: str) -> int:
        """
        Computes the length of code in terms of number of lines.

        :param code: The code snippet.
        :type code: str
        :return: Number of lines in the code.
        :rtype: int
        """
        return len(code.strip().split('\n'))

    def estimate_nesting_depth(self, code: str) -> int:
        """
        Estimates nesting depth by traversing the AST and counting levels of nested statements.

        :param code: The code snippet.
        :type code: str
        :return: Estimated nesting depth.
        :rtype: int
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0

        def get_depth(node, current_depth=0):
            if not isinstance(node, ast.AST):
                return current_depth
            max_depth = current_depth
            for child in ast.iter_child_nodes(node):
                depth = get_depth(child, current_depth + 1)
                if depth > max_depth:
                    max_depth = depth
            return max_depth

        # Subtracts 1 to return to zero-based depth starting at toplevel
        depth = get_depth(tree) - 1
        return max(depth, 0)

    def estimate_variable_usage_difference(self, code_before: str, code_after: str) -> float:
        """
        Estimates the difference in variable usage patterns by counting variable names in both snippets.

        This is a basic heuristic: count Name nodes in AST and compare.

        :param code_before: The code snippet before refactoring.
        :type code_before: str
        :param code_after: The code snippet after refactoring.
        :type code_after: str
        :return: A metric representing variable usage difference.
        :rtype: float
        """
        before_count = self.count_variables(code_before)
        after_count = self.count_variables(code_after)
        return float(after_count - before_count)

    def count_variables(self, code: str) -> int:
        """
        Counts variable names in the code snippet.

        :param code: The code snippet.
        :type code: str
        :return: The number of variable name occurrences.
        :rtype: int
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                count += 1
        return count

    def train_model(self, data_path: str):
        """
        Trains the machine learning model using the given dataset.

        - Splits data into training and testing sets.
        - Performs hyperparameter tuning using GridSearchCV.
        - Evaluates the best model and saves it.

        :param data_path: Path to the CSV file containing the dataset.
        :type data_path: str
        """
        X, y = self.load_data(data_path)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        param_grid = {
            'n_estimators': [50, 100],
            'max_depth': [None, 5],
            'min_samples_split': [2, 5]
        }

        rf = RandomForestClassifier(random_state=42)
        grid_search = GridSearchCV(rf, param_grid, cv=3, scoring='accuracy', n_jobs=-1)
        grid_search.fit(X_train, y_train)

        best_model = grid_search.best_estimator_
        y_pred = best_model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)

        logging.info(f"Model Performance: Accuracy={acc:.2f}, Precision={prec:.2f}, Recall={rec:.2f}")
        logging.info("Saving the trained model to disk.")

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(best_model, f)

        self.model = best_model

    def load_model(self):
        """
        Loads the trained model from disk.
        """
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"No model file found at {self.model_path}")
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)

    def predict_refactoring_error(self, code_before: str, code_after: str) -> float:
        """
        Predicts the probability that a given refactoring introduces an error.

        :param code_before: The code snippet before refactoring.
        :type code_before: str
        :param code_after: The code snippet after refactoring.
        :type code_after: str
        :return: Probability of error introduction.
        :rtype: float
        """
        if self.model is None:
            self.load_model()

        feats = self.extract_features(code_before, code_after)
        X = pd.DataFrame([feats])
        prob = self.model.predict_proba(X)[0][1]
        return prob


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ML Error Filter Tool")
    parser.add_argument("command", choices=["train", "predict"], help="Train the model or predict error probability.")
    parser.add_argument("--data", help="Path to the dataset CSV for training.")
    parser.add_argument("--before", help="Path to code before refactoring for prediction.")
    parser.add_argument("--after", help="Path to code after refactoring for prediction.")

    args = parser.parse_args()

    ml_filter = MLErrorFilter()

    if args.command == "train":
        if not args.data:
            print("You must provide a dataset path with --data to train the model.")
            exit(1)
        ml_filter.train_model(args.data)
        print("Model trained and saved.")
    elif args.command == "predict":
        if not args.before or not args.after:
            print("You must provide --before and --after code paths for prediction.")
            exit(1)

        with open(args.before, 'r', encoding='utf-8') as f:
            code_before = f.read()

        with open(args.after, 'r', encoding='utf-8') as f:
            code_after = f.read()

        error_prob = ml_filter.predict_refactoring_error(code_before, code_after)
        print(f"Predicted error probability: {error_prob:.2f}")