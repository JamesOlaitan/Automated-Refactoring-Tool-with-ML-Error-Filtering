import os
import shutil
import pytest
import subprocess

@pytest.fixture
def temp_output_dir(tmp_path):
    """
    Fixture providing a temporary output directory for refactored files.
    """
    output_dir = tmp_path / "refactored_code"
    output_dir.mkdir()
    return str(output_dir)

def test_cli_on_sample_file(temp_output_dir):
    """
    Tests the CLI on a sample Python file, verifying that
    a refactored output file is created.
    """
    sample_file = os.path.join(os.path.dirname(__file__), "sample_code", "sample_loop.py")
    cmd = [
        "python", 
        "-m", 
        "refactoring_tool.cli",
        sample_file,
        "--output",
        temp_output_dir,
        "-v"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Checks process exit code
    assert result.returncode == 0, f"CLI returned non-zero exit code: {result.stderr}"
    
    # Verifies that refactored file exists in output dir
    output_file = os.path.join(temp_output_dir, "sample_loop.py")
    assert os.path.exists(output_file), "Refactored file should exist in output directory."

def test_cli_on_directory(temp_output_dir):
    """
    Tests the CLI on a directory containing multiple Python files.
    """
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_code")
    cmd = [
        "python", 
        "-m", 
        "refactoring_tool.cli",
        sample_dir,
        "--output",
        temp_output_dir,
        "-v"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI returned error: {result.stderr}"

    # Checks for presence of refactored files
    expected_files = ["sample_loop.py", "sample_nested_if.py", "sample_if_chain.py", "sample_no_issues.py"]
    for f in expected_files:
        assert os.path.exists(os.path.join(temp_output_dir, f)), f"{f} should be refactored."

def test_cli_nonexistent_file(temp_output_dir):
    """
    Tests how the CLI handles a non-existent input path.
    """
    cmd = [
        "python", 
        "-m", 
        "refactoring_tool.cli",
        "non_existent_file.py",
        "--output",
        temp_output_dir
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # The CLI should exit with code 1
    assert result.returncode == 1, "Should exit with code 1 for non-existent file."
    assert "not a valid file or directory" in result.stdout