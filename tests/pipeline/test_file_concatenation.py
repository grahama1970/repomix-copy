"""Test for file concatenation functionality."""
import pytest
from pathlib import Path
from repomix.utils.parser import concatenate_files

def test_file_concatenation_format():
    """Test file concatenation format requirements."""
    # Create test files
    test_dir = Path("tests/temp")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    files = []
    for i in range(3):
        file_path = test_dir / f"test{i}.txt"
        file_path.write_text(f"Test content {i}\n")
        files.append(file_path)
    
    try:
        # Concatenate files
        content = concatenate_files(files, test_dir, "https://github.com/test/repo", "/test/dir")
        
        # Split content into sections
        sections = [s.strip() for s in content.split('\n\n') if s.strip()]
        
        # First section should be metadata
        assert sections[0].startswith('# Metadata'), "First section should be metadata"
        metadata_lines = sections[0].split('\n')
        assert len(metadata_lines) >= 5, "Metadata should have at least 5 lines"
        assert 'total_tokens:' in metadata_lines[1]
        assert 'file_count:' in metadata_lines[2]
        assert 'repository:' in metadata_lines[3]
        assert 'target_directory:' in metadata_lines[4]
        assert 'generated:' in metadata_lines[5]
        
        # Remaining sections should be files
        for section in sections[1:]:
            lines = section.split('\n')
            assert lines[0].startswith('File:'), f"File section should start with 'File:', got: {lines[0]}"
            assert len(lines) > 1, "File section should have content"
    finally:
        # Cleanup test files
        for file in files:
            file.unlink(missing_ok=True)
        test_dir.rmdir() 