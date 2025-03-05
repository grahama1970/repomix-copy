"""Test for repository cloning functionality."""
import pytest
from pathlib import Path
from repomix.utils.git import clone_repository, cleanup_repository

def test_repository_cloning():
    """Test cloning a repository."""
    repo_url = "https://github.com/raycast/script-commands"
    branch = "master"
    
    repo_dir = clone_repository(repo_url, branch)
    try:
        assert repo_dir.exists()
        assert (repo_dir / "commands").exists()
        assert (repo_dir / ".git").exists()
    finally:
        cleanup_repository(repo_dir)
        assert not repo_dir.exists() 