"""Tests for file operations utilities."""
import os
from pathlib import Path
import pytest
from loguru import logger
from repomix.utils.file_utils import (
    read_file,
    write_file,
    save_json,
    load_json,
    collect_files,
    clean_directory,
    is_binary_file,
    is_text_file,
    get_file_extension
)

def test_read_write_file(tmp_path):
    """Test reading and writing files."""
    test_file = tmp_path / "test.txt"
    content = "Hello, World!"
    
    write_file(test_file, content)
    assert test_file.exists()
    
    read_content = read_file(test_file)
    assert read_content == content

def test_json_operations(tmp_path):
    """Test JSON file operations."""
    test_file = tmp_path / "test.json"
    data = {"key": "value"}
    
    save_json(test_file, data)
    assert test_file.exists()
    
    loaded_data = load_json(test_file)
    assert loaded_data == data

def test_collect_files(tmp_path):
    """Test collecting files with ignore patterns."""
    # Create test files
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.py").write_text("content2")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__/cache.pyc").write_text("cache")
    
    # Test without ignore patterns
    files = collect_files(tmp_path)
    assert len(files) == 3  # Including the cache file
    
    # Test with ignore patterns
    files = collect_files(tmp_path, ["*.pyc", "__pycache__/*"])
    assert len(files) == 2
    assert all(f.suffix in [".txt", ".py"] for f in files)

def test_clean_directory(tmp_path):
    """Test directory cleaning."""
    # Create test structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir/file2.txt").write_text("content2")
    
    clean_directory(test_dir)
    assert not test_dir.exists()

def test_file_type_detection(tmp_path):
    """Test file type detection."""
    # Text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("Hello")
    assert is_text_file(text_file)
    assert not is_binary_file(text_file)
    
    # Python file
    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')")
    assert is_text_file(py_file)
    assert not is_binary_file(py_file)
    
    # Get extension
    assert get_file_extension(text_file) == "txt"
    assert get_file_extension(py_file) == "py"

def test_error_handling(tmp_path):
    """Test error handling in file operations."""
    # Test non-existent file
    with pytest.raises(FileNotFoundError):
        read_file(tmp_path / "nonexistent.txt")
    
    # Test invalid JSON
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{invalid:json}")
    with pytest.raises(Exception):
        load_json(invalid_json)
    
    # Test non-existent directory
    with pytest.raises(FileNotFoundError):
        collect_files(tmp_path / "nonexistent") 