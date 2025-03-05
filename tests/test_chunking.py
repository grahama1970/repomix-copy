import pytest
from typing import Dict
from repomix.utils.parser import chunk_content
from repomix.utils.spacy_utils import count_tokens

def test_chunking_under_limit():
    """Test that when total content is under the token limit, a single chunk is produced."""
    content = {
        "file1.py": "print('hello world')",
        "file2.py": "print('another file')"
    }
    chunks = chunk_content(content, token_limit=4000)
    assert len(chunks) == 1, "Expected one chunk for content under limit"
    for filename in content.keys():
        assert f"File: {filename}" in chunks[0], f"Header for {filename} missing"

def test_chunking_over_limit():
    """Test that a large file is split into multiple chunks with sequential headers."""
    # Create a large content that will force splitting
    large_content = "line\n" * 5000  
    content = {"big_file.py": large_content}
    chunks = chunk_content(content, token_limit=4000)
    
    assert len(chunks) > 1, "Expected multiple chunks for an over-limit file"
    
    # Verify sequential numbering
    seen_numbers = set()
    for chunk in chunks:
        # Each chunk should start with a header
        assert chunk.startswith("File:"), "Chunk does not start with 'File:' header"
        header = chunk.split("\n", 1)[0]
        # Extract the numeric prefix
        prefix = header.split("_")[0].split(" ")[1]  # "File: 001" -> "001"
        assert len(prefix) == 3, "Expected 3-digit numeric prefix"
        assert prefix.isdigit(), "Prefix should be numeric"
        seen_numbers.add(int(prefix))
    
    # Verify numbers are sequential
    expected_numbers = set(range(1, len(chunks) + 1))
    assert seen_numbers == expected_numbers, "Chunk numbers should be sequential"

def test_chunking_newline_handling():
    """Test that each chunk does not have leading or trailing extraneous newlines."""
    content = {
        "file1.py": "def func():\n    pass",
        "file2.py": "def another():\n    pass"
    }
    chunks = chunk_content(content, token_limit=4000)
    for chunk in chunks:
        assert not chunk.startswith("\n"), "Chunk should not start with a newline"
        assert not chunk.endswith("\n"), "Chunk should not end with a newline"
        assert chunk.startswith("File:"), "Chunk should start with 'File:' header"

def test_chunking_file_combining():
    """Test that files are combined into chunks when possible."""
    content = {
        "a.py": "print('first')",
        "b.py": "print('second')",
        "c.py": "print('third')"
    }
    
    # Set a token limit that should allow at least two files per chunk
    small_limit = count_tokens("File: a.py\nprint('first')") * 2 + 10
    
    chunks = chunk_content(content, token_limit=small_limit)
    assert 1 < len(chunks) < len(content), "Files should be combined when possible"
    
    # Verify all files are present
    all_content = "\n".join(chunks)
    for filename in content.keys():
        assert f"File: {filename}" in all_content, f"Missing file: {filename}"

def test_single_line_over_limit():
    """Test handling of a single line that exceeds the token limit."""
    # Create a string that will definitely exceed 4000 tokens
    # Using varied text to avoid token compression
    long_text = " ".join([f"unique_token_{i}" for i in range(5000)])  # This will create >4000 tokens
    content = {"long_line.py": long_text}
    chunks = chunk_content(content, token_limit=4000)
    
    assert len(chunks) > 1, "Long line should be split into multiple chunks"
    for chunk in chunks:
        assert chunk.startswith("File: "), "Each chunk should have a header"
        assert count_tokens(chunk) <= 4000, "Each chunk should be under token limit"

def test_empty_file_handling():
    """Test that empty files are handled correctly."""
    content = {
        "empty.py": "",
        "normal.py": "print('hello')"
    }
    chunks = chunk_content(content, token_limit=4000)
    
    # Empty file should still have a header
    all_content = "\n".join(chunks)
    assert "File: empty.py" in all_content, "Empty file should have a header"
    assert "File: normal.py" in all_content, "Normal file should be present"

def test_small_token_limit():
    """Test behavior with a very small token limit."""
    content = {"test.py": "print('hello')\nprint('world')"}
    # Set limit smaller than a single line + header
    small_limit = 5
    chunks = chunk_content(content, token_limit=small_limit)
    
    # Verify each chunk is properly formatted even with tiny limit
    for chunk in chunks:
        assert chunk.startswith("File: "), "Each chunk should have a header"
        assert count_tokens(chunk) > 0, "Chunks should not be empty"

def test_deterministic_output():
    """Test that chunking produces the same output for the same input."""
    content = {
        "b.py": "print('second')",
        "a.py": "print('first')",
        "c.py": "print('third')"
    }
    
    chunks1 = chunk_content(content, token_limit=4000)
    chunks2 = chunk_content(content, token_limit=4000)
    
    assert chunks1 == chunks2, "Chunking should be deterministic"
    # Verify files are processed in sorted order
    all_content = "\n".join(chunks1)
    assert all_content.index("File: a.py") < all_content.index("File: b.py"), "Files should be processed in sorted order" 