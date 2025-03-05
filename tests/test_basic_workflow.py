"""Test the basic workflow of repomix."""
import pytest
from pathlib import Path
import json
from repomix.utils.git import parse_github_url, clone_repository, cleanup_repository
from repomix.utils.parser import glob_files, concatenate_files
from repomix.utils.llm import query_model, save_response
from click.testing import CliRunner
from repomix.cli import cli

# Real repository URL for testing
TEST_URL = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
TEST_MODEL = "gpt-4o-mini"
TEST_QUESTION = "What do these scripts do?"

@pytest.mark.asyncio
async def test_basic_url_workflow():
    """Test the most basic workflow with a real GitHub repository."""
    # 1. Parse URL
    repo_url, branch, target_dir = parse_github_url(TEST_URL)
    assert repo_url == "https://github.com/raycast/script-commands"
    assert branch == "master"
    assert target_dir == "/commands/browsing"
    
    # 2. Clone real repo
    repo_dir = clone_repository(repo_url, branch)
    try:
        assert repo_dir.exists()
        target_path = repo_dir / target_dir.lstrip('/')
        assert target_path.exists()
        
        # 3. Find actual files
        ignore_patterns = ["*.pyc", "__pycache__/*", "*.png", "*.jpg", "images/*"]
        files = glob_files(repo_dir, target_dir, ignore_patterns)
        assert len(files) > 0
        
        # 4. Concatenate real files
        content = concatenate_files(files, repo_dir, TEST_URL, target_dir)
        assert len(content) > 0
        
        # Save concatenated content for verification
        output_dir = Path("tests/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "concatenated.txt").write_text(content)
        
        # 5. Query real LLM
        system_prompt = f"Analyze these scripts and answer: {TEST_QUESTION}"
        response = await query_model(TEST_MODEL, content, system_prompt)
        
        # Save and verify real response
        response_path = output_dir / "response.json"
        save_response(response, response_path)
        
        # Verify response structure
        response_data = json.loads(response_path.read_text())
        assert "response" in response_data
        assert "metadata" in response_data
        assert "usage" in response_data
        assert response_data["usage"]["total_tokens"] > 0
        
    finally:
        # Clean up real repository
        cleanup_repository(repo_dir)

def test_ask_command():
    """Test the ask command with a real directory."""
    # Use an actual directory from the project
    test_dir = Path("src/repomix")
    assert test_dir.exists(), "Test directory must exist"
    
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, [
        "ask",
        str(test_dir),
        "What does this code do?",
        "--model-id", TEST_MODEL
    ])
    
    # Verify actual command behavior
    assert result.exit_code == 0
    assert "Starting analysis of repository" in result.stderr

def test_ask_error_handling():
    """Test error handling with real error conditions."""
    runner = CliRunner(mix_stderr=False)
    
    # Test with actual non-existent directory
    result = runner.invoke(cli, [
        "ask",
        "/nonexistent/path",
        "What does the code do?",
        "--model-id", TEST_MODEL
    ])
    
    # Verify real error message
    assert "Directory '/nonexistent/path' does not exist" in result.stderr
    assert result.exit_code == 1