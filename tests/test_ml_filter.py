import pytest
import os
import pandas as pd
import tempfile

from refactoring_tool.ml_filter import MLErrorFilter

def test_feature_extraction():
    """
    Tests the feature extraction method with dummy code.
    """
    ml_filter = MLErrorFilter()
    code_before = "result = []\nfor i in range(10):\n    result.append(i)\n"
    code_after = "result = [i for i in range(10)]\n"
    feats = ml_filter.extract_features(code_before, code_after)
    expected_keys = {
        'complexity_before', 'complexity_after', 'complexity_change',
        'length_before', 'length_after', 'length_change',
        'nesting_before', 'nesting_after', 'nesting_change',
        'variable_usage_diff'
    }
    assert expected_keys.issubset(feats.keys())

def test_train_and_predict():
    """
    Tests the training and prediction process with a tiny synthetic dataset.
    """
    ml_filter = MLErrorFilter(model_path="test_model.pkl")

    # Creates a small CSV in a temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp.write("code_before,code_after,error_introduced\n")
        tmp.write("\"print('hello')\",\"print('hello world')\",0\n")
        tmp.write("\"x = 0\\nif x == 0:\\n    print('Zero')\",\"x = 0\\nif x == 0:\\n    print('Changed')\",1\n")
        tmp_name = tmp.name

    try:
        ml_filter.train_model(tmp_name)
        # Simple test to ensure model is created
        assert os.path.exists("test_model.pkl")

        # Predicts on a new snippet
        prob = ml_filter.predict_refactoring_error("x=0", "x=1")
        assert 0.0 <= prob <= 1.0, "Prediction probability should be between 0 and 1."
    finally:
        # Cleanup
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        if os.path.exists("test_model.pkl"):
            os.remove("test_model.pkl")