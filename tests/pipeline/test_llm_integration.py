"""Test for LLM integration functionality."""
import pytest
from repomix.utils.llm import query_model
from repomix.utils.models import LLMResponse, TokenUsage

TEST_MODEL = "gpt-3.5-turbo"
TEST_QUESTION = "What do these scripts do?"

@pytest.mark.asyncio
async def test_llm_query_format():
    """Test LLM query with proper format."""
    test_content = """File: commands/browsing/test.js
console.log('test');

File: commands/browsing/other.js
function hello() { return 'world'; }
"""
    system_prompt = f"Analyze these scripts and answer: {TEST_QUESTION}"
    response = await query_model(TEST_MODEL, test_content, system_prompt)
    
    # Verify response is properly structured
    assert isinstance(response, LLMResponse)
    assert isinstance(response.id, str)
    assert isinstance(response.response, str)
    assert len(response.response) > 0
    assert isinstance(response.metadata, dict)
    # Model name might include version suffix
    assert response.metadata["model"].startswith(TEST_MODEL)
    assert isinstance(response.usage, TokenUsage)
    assert response.usage.total_tokens == response.usage.completion_tokens + response.usage.prompt_tokens 