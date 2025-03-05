"""Test repomix with Raycast browsing scripts."""
# Note: Pydantic deprecation warnings are from dependencies using older Pydantic patterns.
# These warnings can be safely ignored as they don't affect our code's functionality.
# Our own models use the recommended ConfigDict approach.

import pytest
import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator
from loguru import logger
from repomix.utils.git import parse_github_url, clone_repository, cleanup_repository
from repomix.utils.parser import glob_files, concatenate_files
from repomix.utils.llm import query_model, save_response, initialize_litellm_cache
from repomix.utils.file_utils import load_env_file
from repomix.utils.models import LLMResponse, TokenUsage, Message, LLMRequest
from litellm import acompletion
import litellm


TEST_REPO_URL = "https://github.com/raycast/script-commands/tree/master/commands/browsing"
TEST_MODEL = "gpt-4o-mini"
DEFAULT_IGNORE_PATTERNS = [
    "*.pyc",
    "__pycache__/*",
    ".git/*",
    ".github/*",
    "*.log",
    "*.md",
    "*.txt",
    "*.json",
    "*.yaml",
    "*.yml"
]


@pytest.fixture(autouse=True)
def load_env():
    """Load environment variables before running tests."""
    load_env_file()


@pytest.fixture
def output_dir(tmp_path):
    """Create temporary output directory."""
    return tmp_path / "output"


@pytest.fixture
async def repo_setup():
    """Set up repository and clean up after test."""
    repo_url, branch, target_dir = parse_github_url(TEST_REPO_URL)
    if not branch:
        branch = "master"
    repo_dir = clone_repository(repo_url, branch)
    
    try:
        yield repo_dir, target_dir
    finally:
        cleanup_repository(repo_dir)


@pytest.fixture(scope="function")
def initialize_cache():
    """Initialize Redis cache for each test."""
    initialize_litellm_cache()
    yield
    # Clean up cache after test if needed
    litellm.cache = None


@pytest.mark.asyncio
async def test_litellm_basic():
    """Test basic async completion with mock response."""
    try:
        response = await acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello world"}],
            mock_response="Hello! How can I help you today?"
        )
        assert response.choices[0].message.content == "Hello! How can I help you today?"
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


@pytest.mark.asyncio
async def test_github_url_parsing():
    """Test parsing of GitHub repository URL."""
    repo_url, branch, target_dir = parse_github_url(TEST_REPO_URL)
    assert repo_url == "https://github.com/raycast/script-commands"
    assert branch == "master"
    assert target_dir == "/commands/browsing"


@pytest.mark.asyncio
async def test_repository_setup(repo_setup):
    """Test repository setup and cleanup."""
    repo_dir, target_dir = repo_setup
    assert repo_dir.exists(), "Repository directory not created"
    target_path = repo_dir / target_dir.lstrip('/')
    assert target_path.exists(), "Target directory not found"


@pytest.mark.asyncio
async def test_file_globbing(repo_setup):
    """Test file globbing and filtering."""
    repo_dir, target_dir = repo_setup
    ignore_patterns = [
        "*.pyc",
        "__pycache__/*",
        ".git/*",
        ".github/*",
        "*.log",
        "*.md",
        "*.txt",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.ico",
        "*.svg",
        "images/*"
    ]
    
    files = glob_files(repo_dir, target_dir, ignore_patterns)
    assert len(files) > 0, "No files found in repository"
    assert all(not f.match("*.png") for f in files), "Image files should be filtered"


@pytest.mark.asyncio
async def test_file_concatenation(repo_setup, output_dir):
    """Test file concatenation."""
    repo_dir, target_dir = repo_setup
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = glob_files(repo_dir, target_dir, ["*.pyc"])  # Minimal ignore pattern for test
    content = concatenate_files(files, repo_dir, TEST_REPO_URL, target_dir)
    
    concat_path = output_dir / "concatenated.txt"
    concat_path.write_text(content)
    
    assert concat_path.exists(), "Concatenated file not created"
    assert len(content) > 0, "Concatenated content is empty"


@pytest.mark.asyncio
async def test_model_query_mock():
    """Test model querying with mock response."""
    mock_content = "Test content"
    mock_system_prompt = "Test analysis"
    mock_response_text = "Mocked analysis result"
    
    try:
        response = await query_model(
            TEST_MODEL,
            mock_content,
            mock_system_prompt
        )
        assert response is not None, "No response received"
    except Exception as e:
        pytest.fail(f"Error querying model: {e}")


@pytest.mark.asyncio
async def test_response_saving(output_dir):
    """Test saving model response."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mock_response = LLMResponse(
        id="test-id",
        response="Test response",
        metadata={"model": "test-model"},
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    )
    response_path = output_dir / "response.json"
    
    save_response(mock_response, response_path)
    
    assert response_path.exists(), "Response file not created"
    saved_data = json.loads(response_path.read_text())
    assert "response" in saved_data, "No response in output"
    assert "metadata" in saved_data, "No metadata in output"


@pytest.mark.asyncio
async def test_full_integration(repo_setup, output_dir):
    """Test full integration of all components."""
    repo_dir, target_dir = repo_setup
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find and process files
    files = glob_files(repo_dir, target_dir, ["*.pyc"])
    content = concatenate_files(files, repo_dir, TEST_REPO_URL, target_dir)
    
    # Query model with mock
    system_prompt = "Analyze these scripts and explain what they do."
    response = await query_model(TEST_MODEL, content, system_prompt)
    
    # Type assertion since we know this is not a streaming response
    assert not isinstance(response, AsyncGenerator)
    llm_response: LLMResponse = response  # type: ignore
    
    # Save response
    response_path = output_dir / "response.json"
    save_response(llm_response, response_path)
    
    assert response_path.exists(), "Response file not created"
    response_data = json.loads(response_path.read_text())
    assert "response" in response_data, "No response in output"
    assert "metadata" in response_data, "No metadata in output"


@pytest.mark.asyncio
async def test_raycast_browsing_analysis():
    """Test analyzing Raycast browsing scripts directory."""
    try:
        # Parse repository URL
        repo_url, branch, target_dir = parse_github_url(TEST_REPO_URL)
        assert branch == "master"  # Ensure branch is not None
        
        # Clone repository
        repo_dir = clone_repository(repo_url, branch)
        try:
            # Find relevant files
            files = glob_files(repo_dir, target_dir, DEFAULT_IGNORE_PATTERNS)
            assert files, "No files found in browsing directory"
            
            # Concatenate files
            content = concatenate_files(files, repo_dir, repo_url, target_dir)
            assert content, "Failed to concatenate files"
            
            # Initialize caching
            initialize_litellm_cache()
            
            # Create system prompt
            system_prompt = """You are a helpful assistant analyzing a directory of Raycast script commands.
            Please describe the purpose and functionality of these scripts in a clear and concise way.
            Focus on what types of browsing-related tasks these scripts help automate."""
            
            # Query model
            response = await query_model(
                TEST_MODEL,
                content,
                system_prompt=system_prompt
            )
            
            # Type assertion since we know this is not a streaming response
            assert not isinstance(response, AsyncGenerator)
            llm_response: LLMResponse = response  # type: ignore
            
            # Validate response structure
            assert isinstance(llm_response, LLMResponse)
            assert llm_response.id
            assert llm_response.response
            assert llm_response.metadata
            assert llm_response.usage
            
            # Log response for manual verification
            logger.info(f"Model response: {llm_response.response}")
            logger.info(f"Token usage: {llm_response.usage}")
            
            # Print response for direct visibility
            print("\nModel Response:")
            print("==============")
            print(llm_response.response)
            print("\nToken Usage:")
            print(f"Completion tokens: {llm_response.usage.completion_tokens}")
            print(f"Prompt tokens: {llm_response.usage.prompt_tokens}")
            print(f"Total tokens: {llm_response.usage.total_tokens}")
            print("==============\n")
            
        finally:
            # Clean up cloned repository
            cleanup_repository(repo_dir)
            
    except Exception as e:
        logger.error(f"Error in raycast browsing test: {e}")
        raise 


@pytest.mark.asyncio
async def test_redis_cache_hit(initialize_cache):
    """Test Redis caching with a simple query."""
    # Ensure cache is enabled
    assert litellm.cache is not None, "Cache should be initialized"

    # Create test messages
    test_messages = [
        {"role": "user", "content": "What is the capital of France?"}
    ]

    # First call should miss cache
    logger.info("Testing cache with completion call...")
    response1 = litellm.completion(
        model="gpt-4o-mini",
        messages=test_messages,
        cache={"no-cache": False}
    )
    logger.info(f"First call usage: {response1.usage}")
    if m := response1._hidden_params.get("cache_hit"):
        logger.info(f"Response 1: Cache hit: {m}")

    # Wait for cache to be written
    await asyncio.sleep(1)

    # Second call should hit cache
    response2 = litellm.completion(
        model="gpt-4o-mini",
        messages=test_messages,
        cache={"no-cache": False}
    )
    logger.info(f"Second call usage: {response2.usage}")
    if m := response2._hidden_params.get("cache_hit"):
        logger.info(f"Response 2: Cache hit: {m}")

    # Verify cache hit and response match
    assert response2._hidden_params.get("cache_hit") is True, "Second call should be a cache hit"
    assert response1.choices[0].message.content == response2.choices[0].message.content, "Responses should match" 