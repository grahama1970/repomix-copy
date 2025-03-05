"""Test for URL parsing functionality."""
import pytest
from repomix.utils.git import parse_github_url

def test_directory_url_parsing():
    """Test parsing a directory URL."""
    url = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
    repo_url, branch, target_dir = parse_github_url(url)
    assert repo_url == "https://github.com/raycast/script-commands"
    assert branch == "master"
    assert target_dir == "/commands/browsing" 