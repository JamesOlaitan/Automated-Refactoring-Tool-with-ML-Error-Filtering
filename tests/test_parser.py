import pytest
import os
from parser import analyze_file

@pytest.fixture
def sample_code_dir():
    """
    Fixture to provide the path to the sample code directory.

    :return: Path to the sample code directory.
    """
    return os.path.join(os.path.dirname(__file__), 'sample_code')

def test_loop_detection(sample_code_dir):
    """
    Tests if the parser correctly identifies inefficient loops.

    :param sample_code_dir: Fixture providing the sample code directory path.
    """
    file_path = os.path.join(sample_code_dir, 'sample_loop.py')
    loop_issues, _, _ = analyze_file(file_path)

    assert len(loop_issues) == 1, "Should detect one inefficient loop."
    issue = loop_issues[0]
    assert "For-loop can be converted to a list comprehension." in issue['message']

def test_nested_if_detection(sample_code_dir):
    """
    Tests if the parser correctly identifies nested if-statements.

    :param sample_code_dir: Fixture providing the sample code directory path.
    """
    file_path = os.path.join(sample_code_dir, 'sample_nested_if.py')
    _, nested_if_issues, _ = analyze_file(file_path)

    assert len(nested_if_issues) == 1, "Should detect one nested if-statement."
    issue = nested_if_issues[0]
    assert "Nested if-statements can be merged." in issue['message']

def test_if_chain_detection(sample_code_dir):
    """
    Tests if the parser correctly identifies if-elif-else chains.

    :param sample_code_dir: Fixture providing the sample code directory path.
    """
    file_path = os.path.join(sample_code_dir, 'sample_if_chain.py')
    _, _, if_chain_issues = analyze_file(file_path)

    assert len(if_chain_issues) == 1, "Should detect one if-elif-else chain."
    issue = if_chain_issues[0]
    assert "If-elif-else chain can be replaced with a dictionary." in issue['message']

def test_no_issues(sample_code_dir):
    """
    Tests if the parser correctly handles code with no issues.

    :param sample_code_dir: Fixture providing the sample code directory path.
    """
    file_path = os.path.join(sample_code_dir, 'sample_no_issues.py')
    loop_issues, nested_if_issues, if_chain_issues = analyze_file(file_path)

    total_issues = len(loop_issues) + len(nested_if_issues) + len(if_chain_issues)
    assert total_issues == 0, "Should detect no issues."

def test_syntax_error_handling(tmp_path):
    """
    Tests if the parser handles syntax errors gracefully.

    :param tmp_path: Fixture providing a temporary directory.
    """
    code_with_error = "def faulty_function(:\n    pass"

    file_path = tmp_path / "faulty.py"
    file_path.write_text(code_with_error)

    with pytest.raises(SyntaxError):
        analyze_file(str(file_path))

def test_file_not_found():
    """
    Tests if the parser handles file not found errors gracefully.
    """
    file_path = "non_existent_file.py"

    with pytest.raises(FileNotFoundError):
        analyze_file(file_path)