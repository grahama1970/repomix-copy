"""Test for file discovery functionality."""
import pytest
from repomix.utils.git import clone_repository, cleanup_repository
from repomix.utils.parser import glob_files

def test_file_globbing_with_filters():
    """Test file discovery with ignore patterns."""
    repo_url = "https://github.com/raycast/script-commands"
    branch = "master"
    target_dir = "/commands/browsing"
    
    repo_dir = clone_repository(repo_url, branch)
    try:
        ignore_patterns = [
            "*.pyc", "__pycache__/*", 
            "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
            "images/*", "*.md", "*.txt"
        ]
        files = glob_files(repo_dir, target_dir, ignore_patterns)
        
        assert len(files) > 0
        for file in files:
            # Verify no ignored files are included
            assert not any(file.match(pattern) for pattern in ignore_patterns)
            # Verify files are within target directory
            assert str(file).startswith(str(repo_dir / target_dir.lstrip('/')))
            # Verify files are code files
            assert file.suffix in ['.js', '.ts', '.py', '.sh', '.rb', '.applescript'], \
                f"Unexpected file type: {file.suffix}"
    finally:
        cleanup_repository(repo_dir) 