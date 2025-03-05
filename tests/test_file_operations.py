"""Tests for file operations utilities."""
import os
from pathlib import Path
import pytest
from loguru import logger
from repomix.utils.file_operations import (
    read_file,
    write_file,
    save_json,
    load_json,
    collect_files,
    ensure_directory,
    get_file_size,
    is_binary_file,
    get_file_extension,
    is_text_file,
    clean_directory
)

def test_read_write_file():
    """Test reading and writing files using real project files."""
    logger.info("Testing read_write_file")
    
    # Use real project files
    test_file = Path("src/repomix/utils/file_operations.py")
    assert test_file.exists(), "Test file should exist"
    
    # Read real file content
    content = read_file(test_file)
    assert "def read_file" in content, "Should contain file operation functions"
    
    # Test writing to data directory
    output_file = Path("data/test_output.txt")
    write_file(output_file, content)
    assert output_file.exists(), "Output file should exist"
    assert read_file(output_file) == content, "Written content should match"
    
    # Clean up
    output_file.unlink()
    logger.info("Read/write test completed successfully")

def test_json_operations():
    """Test JSON operations with real project configuration."""
    logger.info("Testing JSON operations")
    
    # Use real project configuration
    data = {
        "name": "repomix",
        "version": "0.1.0",
        "description": "Repository content mixer"
    }
    
    # Save to data directory
    test_file = Path("data/test_config.json")
    save_json(test_file, data)
    assert test_file.exists(), "JSON file should exist"
    
    loaded_data = load_json(test_file)
    assert loaded_data == data, "Loaded JSON should match original"
    
    # Clean up
    test_file.unlink()
    logger.info("JSON operations test completed successfully")

def test_collect_files():
    """Test file collection with real project structure."""
    logger.info("Testing file collection")
    
    # Use real project source directory
    src_dir = Path("src/repomix")
    
    # Test without ignore patterns
    files = collect_files(src_dir)
    assert any(f.name == "main.py" for f in files), "Should find main.py"
    assert any(f.name == "cli.py" for f in files), "Should find cli.py"
    
    # Test with ignore patterns
    ignore_patterns = ["*.pyc", "__pycache__/*", "*.log"]
    filtered_files = collect_files(src_dir, ignore_patterns)
    assert all(not f.name.endswith(".pyc") for f in filtered_files), "Should exclude .pyc files"
    
    logger.info("File collection test completed successfully")

def test_directory_operations():
    """Test directory operations with real project structure."""
    logger.info("Testing directory operations")
    
    # Use real project data directory
    test_dir = Path("data/test_output")
    
    # Clean up first in case previous test failed
    if test_dir.exists():
        clean_directory(test_dir)
    
    created_dir = ensure_directory(test_dir)
    assert created_dir.exists(), "Directory should be created"
    
    # Create test files in project structure
    (test_dir / "temp.txt").write_text("test")
    
    # Clean directory and verify
    clean_directory(test_dir)
    assert not test_dir.exists(), "Directory should be removed"
    assert Path("data").exists(), "Parent directory should remain"
    
    logger.info("Directory operations test completed successfully")

def test_file_type_detection():
    """Test file type detection with real project files."""
    logger.info("Testing file type detection")
    
    # Use real project files
    python_file = Path("src/repomix/main.py")
    text_file = Path("README.md")
    
    # Test extension detection
    assert get_file_extension(python_file) == "py"
    assert get_file_extension(text_file) == "md"
    
    # Test binary/text detection
    assert not is_binary_file(python_file), "Python file should not be binary"
    assert is_text_file(python_file), "Python file should be text"
    assert is_text_file(text_file), "Markdown file should be text"
    
    logger.info("File type detection test completed successfully")

def test_error_handling():
    """Test error handling with real file paths."""
    logger.info("Testing error handling")
    
    # Test with non-existent project file
    non_existent = Path("src/repomix/does_not_exist.py")
    with pytest.raises(FileNotFoundError):
        read_file(non_existent)
    
    # Test with invalid project path
    invalid_path = Path("src/invalid/path/file.txt")
    write_file(invalid_path, "test")  # Should create directories
    assert invalid_path.exists(), "Should create necessary directories"
    
    # Clean up in correct order (deepest first)
    invalid_path.unlink()  # Remove file first
    invalid_path.parent.rmdir()  # Remove deepest directory
    invalid_path.parent.parent.rmdir()  # Remove parent directory
    
    logger.info("Error handling test completed successfully")

def test_file_size():
    """Test file size calculation with real project files."""
    logger.info("Testing file size calculation")
    
    # Use real project file
    test_file = Path("src/repomix/main.py")
    size = get_file_size(test_file)
    assert size > 0, "File size should be positive"
    assert size == test_file.stat().st_size, "Size should match filesystem"
    
    logger.info("File size test completed successfully") 