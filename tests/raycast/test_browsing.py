"""Test for raycast browsing functionality."""
import pytest
from pathlib import Path
from repomix.utils.git import parse_github_url, clone_repository, cleanup_repository
from repomix.utils.parser import glob_files

def test_raycast_browsing():
    """Test browsing raycast script commands."""
    url = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
    repo_url, branch, target_dir = parse_github_url(url)
    assert branch == "master"  # Ensure branch is not None
    
    repo_dir = clone_repository(repo_url, branch)
    try:
        # Test browsing scripts
        files = glob_files(repo_dir, target_dir, ["*.md", "*.txt"])
        assert len(files) > 0
        
        # Verify script types
        script_types = {file.suffix for file in files}
        assert script_types.intersection({'.js', '.ts', '.py', '.sh', '.rb', '.applescript'})
        
        # Verify script locations
        for file in files:
            assert str(file).startswith(str(repo_dir / "commands/browsing"))
            assert file.exists()
    finally:
        cleanup_repository(repo_dir) 