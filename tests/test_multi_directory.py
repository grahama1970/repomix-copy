"""Tests for multi-directory analysis functionality."""
from pathlib import Path
import pytest
from click.testing import CliRunner
from repomix.cli import parse_multi_urls, analyze, cli
import redis
import litellm
import os
from loguru import logger
from repomix.utils.file_utils import load_env_file
from repomix.utils.multi_directory import (
    analyze_directories,
    combine_results,
    process_directory,
    validate_directories
)
from repomix.utils.llm import initialize_litellm_cache
from unittest.mock import patch

# Test URLs for different scenarios
SINGLE_URL = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
MULTI_URLS = [
    "https://github.com/raycast/script-commands/tree/master/commands/browsing",
    "@commands/dashboard"
]
INVALID_MULTI_URLS = [
    "https://github.com/raycast/script-commands/tree/master/commands/browsing",
    "https://github.com/different/repo/tree/master/dir"
]

@pytest.fixture(autouse=True)
def setup_litellm():
    """Set up LiteLLM cache and API keys before each test."""
    # Load environment variables from .env file
    try:
        load_env_file()
    except FileNotFoundError:
        # If .env file not found, set a test key
        os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Initialize LiteLLM cache
    initialize_litellm_cache()
    
    # Mock LiteLLM completion for testing
    async def mock_completion(**kwargs):
        # Raise NotFoundError for invalid model IDs
        if kwargs.get("model") == "openai/gpt-5":
            raise litellm.NotFoundError(
                message="Model not found: openai/gpt-5",
                model="openai/gpt-5",
                llm_provider="openai"
            )
            
        return litellm.ModelResponse(
            id="test-id",
            choices=[
                litellm.Choices(
                    message=litellm.Message(
                        content="Test response",
                        role="assistant"
                    ),
                    index=0,
                    finish_reason="stop"
                )
            ],
            model=kwargs.get("model", "openai/gpt-4"),
            usage=litellm.Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
    
    # Patch LiteLLM completion
    with patch("litellm.acompletion", new=mock_completion):
        yield

def test_parse_multi_urls_single():
    """Test parsing a single URL."""
    result = parse_multi_urls(["@https://github.com/raycast/script-commands/tree/master/commands/browsing"])
    assert result.repo_url == "https://github.com/raycast/script-commands"
    assert result.branch == "master"
    assert result.target_dirs == ["commands/browsing"]

def test_parse_multi_urls_multi():
    """Test parsing multiple URLs."""
    # Test with all GitHub URLs
    result = parse_multi_urls([
        "@https://github.com/raycast/script-commands/tree/master/commands/browsing",
        "@https://github.com/raycast/script-commands/tree/master/commands/dashboard"
    ])
    assert result.repo_url == "https://github.com/raycast/script-commands"
    assert result.branch == "master"
    assert len(result.target_dirs) == 2
    assert "commands/browsing" in result.target_dirs
    assert "commands/dashboard" in result.target_dirs
    
    # Test with all local paths
    result = parse_multi_urls([
        "@mock_repo/dir1",
        "@mock_repo/dir2"
    ])
    assert result.repo_url == "mock_repo"
    assert result.branch == "master"
    assert len(result.target_dirs) == 2
    assert "dir1" in result.target_dirs
    assert "dir2" in result.target_dirs

def test_parse_multi_urls_with_at_prefix():
    """Test parsing URLs with @ prefix."""
    result = parse_multi_urls(["@mock_repo/dir1"])
    assert result.repo_url == "mock_repo"
    assert result.branch == "master"
    assert result.target_dirs == ["dir1"]

def test_parse_multi_urls_with_mixed_prefixes():
    """Test parsing URLs with mixed @ prefixes."""
    with pytest.raises(ValueError, match="All URLs must be from the same repository"):
        parse_multi_urls([
            "@https://github.com/raycast/script-commands/tree/master/commands/browsing",
            "mock_repo/dir1"
        ])

def test_parse_multi_urls_with_different_branches():
    """Test parsing URLs with different branches."""
    with pytest.raises(ValueError, match="All URLs must use the same branch"):
        parse_multi_urls([
            "@https://github.com/raycast/script-commands/tree/master/commands/browsing",
            "@https://github.com/raycast/script-commands/tree/main/commands/dashboard"
        ])

def test_parse_multi_urls_invalid():
    """Test parsing invalid URLs."""
    with pytest.raises(ValueError):
        parse_multi_urls([])

def test_analyze_single_directory():
    """Test analyzing a single directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create mock repository structure
        repo_path = Path("mock_repo")
        repo_path.mkdir()
        (repo_path / "dir1").mkdir()
        (repo_path / "dir1" / "test.py").write_text("print('test1')")

        result = runner.invoke(cli, [
            "analyze",
            "@mock_repo/dir1",
            "--model", "openai/gpt-4o-mini"
        ])

        assert result.exit_code == 0
        assert "Processing repository: mock_repo" in result.output
        assert "Branch: master" in result.output

def test_analyze_multiple_directories():
    """Test analyzing multiple directories concurrently."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create mock repository structure
        repo_path = Path("mock_repo")
        repo_path.mkdir()
        (repo_path / "dir1").mkdir()
        (repo_path / "dir2").mkdir()

        # Create test files
        (repo_path / "dir1" / "test.py").write_text("print('test1')")
        (repo_path / "dir2" / "test.py").write_text("print('test2')")

        result = runner.invoke(analyze, [
            "@mock_repo/dir1",
            "@mock_repo/dir2",
            "--model", "openai/gpt-4o-mini",
            "--output-dir", "test_output"
        ])

        assert result.exit_code == 0
        assert "Processing repository: mock_repo" in result.output
        assert "Directories to process: 2" in result.output

def test_analyze_with_combined_analysis():
    """Test analyzing multiple directories with combined analysis."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create mock repository structure
        repo_path = Path("mock_repo")
        repo_path.mkdir()
        (repo_path / "dir1").mkdir()
        (repo_path / "dir2").mkdir()

        # Create test files
        (repo_path / "dir1" / "test.py").write_text("print('test1')")
        (repo_path / "dir2" / "test.py").write_text("print('test2')")

        result = runner.invoke(analyze, [
            "@mock_repo/dir1",
            "@mock_repo/dir2",
            "--model", "openai/gpt-4o-mini",
            "--output-dir", "test_output",
            "--combined-analysis"
        ])

        assert result.exit_code == 0
        assert "Using combined analysis" in result.output

def test_analyze_command_with_invalid_multi_dirs():
    """Test analyze command with invalid multiple directories."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "analyze",
        "@nonexistent/dir1",
        "@nonexistent/dir2",
        "--model", "openai/gpt-4o-mini"
    ])

    assert result.exit_code == 0  # Command succeeds but warns about missing directories
    assert "Directory not found" in result.output

def test_cli_error_handling():
    """Test CLI error handling for invalid directories."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "analyze",
        "@nonexistent/dir",
        "--model", "openai/gpt-4o-mini"
    ])
    assert result.exit_code == 0  # Command succeeds but warns about missing directory
    assert "Directory not found" in result.output

@pytest.mark.asyncio
async def test_validate_directories():
    """Test directory validation with real project directories."""
    logger.info("Testing directory validation")

    # Use real project directories
    valid_dirs = [
        "src/repomix",
        "tests"
    ]

    # Test valid directories
    result = await validate_directories(valid_dirs)
    assert len(result) == 2, "Should validate both directories"
    assert all(isinstance(p, Path) for p in result), "All results should be Path objects"

    # Test invalid directory
    with pytest.raises(ValueError):
        await validate_directories(["nonexistent/dir"])

@pytest.mark.asyncio
async def test_process_directory():
    """Test directory processing with real project structure."""
    logger.info("Testing directory processing")

    # Use real project source directory
    test_dir = Path("src/repomix")

    # Process directory
    result = await process_directory(test_dir)

    # Verify results
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "files" in result, "Result should contain files list"
    assert "content" in result, "Result should contain concatenated content"
    assert len(result["files"]) > 0, "Should find files in the directory"
    assert len(result["content"]) > 0, "Should have concatenated content"

@pytest.mark.asyncio
async def test_combine_results():
    """Test result combination with real project data."""
    logger.info("Testing result combination")

    # Process real project directories
    src_result = await process_directory(Path("src/repomix"))
    test_result = await process_directory(Path("tests"))

    # Combine results
    combined = await combine_results([src_result, test_result])

    # Verify combined results
    assert isinstance(combined, dict), "Combined result should be a dictionary"
    assert "files" in combined, "Combined result should contain files list"
    assert "content" in combined, "Combined result should contain concatenated content"
    assert len(combined["files"]) > 0, "Should have files in combined result"
    assert len(combined["content"]) > 0, "Should have content in combined result"

@pytest.mark.asyncio
async def test_analyze_directories():
    """Test full directory analysis with real LLM calls."""
    logger.info("Testing directory analysis")

    # Use real project directories
    test_dirs = [
        "src/repomix/utils",
        "tests"
    ]

    # Test with real LLM call
    result = await analyze_directories(
        test_dirs,
        model="openai/gpt-4o-mini",
        question="Analyze these directories and summarize their purpose"
    )

    # Verify analysis results
    assert isinstance(result, dict), "Result should be a dictionary"
    if result.get("is_combined", False):
        assert "files" in result, "Combined analysis should have files list"
        assert "analysis" in result, "Combined analysis should have analysis"
    else:
        assert "directory_results" in result, "Separate analysis should have directory results"
        assert len(result["directory_results"]) > 0, "Should have analysis for each directory"

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling with real edge cases."""
    logger.info("Testing error handling")

    # Test with empty directory list
    with pytest.raises(ValueError):
        await analyze_directories(
            [],
            model="openai/gpt-4o-mini",
            question="test"
        )

    # Test with invalid directory
    with pytest.raises(ValueError):
        await validate_directories(["nonexistent/dir"])

    # Test with invalid model ID (404 error according to litellm docs)
    with pytest.raises(litellm.NotFoundError):
        await analyze_directories(
            ["src/repomix"],
            model="openai/gpt-5",  # Using a non-existent GPT model name with prefix
            question="test"
        )

    logger.info("Error handling test completed successfully") 