"""Test for basic workflow functionality."""
import pytest
from pathlib import Path
from repomix.utils.git import parse_github_url, clone_repository, cleanup_repository
from repomix.utils.parser import glob_files, concatenate_files
from repomix.utils.llm import query_model, save_response
from repomix.utils.models import LLMResponse

@pytest.mark.asyncio
async def test_basic_workflow():
    """Test the basic end-to-end workflow."""
    # Test URL parsing
    url = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
    repo_url, branch, target_dir = parse_github_url(url)
    assert branch == "master"  # Ensure branch is not None
    
    # Test repository cloning
    repo_dir = clone_repository(repo_url, branch)
    try:
        # Test file discovery
        files = glob_files(repo_dir, target_dir, ["*.md", "*.txt"])
        assert len(files) > 0
        
        # Test file concatenation
        content = concatenate_files(files, repo_dir, repo_url, target_dir)
        assert content.startswith("# Metadata")
        
        # Test LLM query
        response = await query_model("gpt-3.5-turbo", content, "What do these scripts do?", stream=False)
        assert isinstance(response, LLMResponse)  # Ensure non-streaming response
        assert response.response
        
        # Test response saving
        output_path = Path("tests/output/response.json")
        save_response(response, output_path)
        assert output_path.exists()
    finally:
        cleanup_repository(repo_dir) 