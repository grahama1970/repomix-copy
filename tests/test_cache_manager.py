"""Tests for LiteLLM cache initialization and functionality."""
import pytest
from loguru import logger
from repomix.utils.cache_manager import initialize_litellm_cache
import litellm
import redis
import os

def test_litellm_cache_initialization():
    """Test LiteLLM cache initialization with Redis."""
    logger.info("Testing LiteLLM cache initialization")
    
    # Initialize cache with Redis configuration
    initialize_litellm_cache()
    
    # Verify cache is enabled and using Redis
    assert litellm.cache is not None
    assert litellm.cache.type == "redis"
    
    # Test Redis connection directly
    redis_client = redis.Redis(host="localhost", port=6379)
    assert redis_client.ping(), "Redis server should be reachable"

def test_litellm_cache_fallback():
    """Test fallback to in-memory cache when Redis fails."""
    logger.info("Testing LiteLLM cache fallback")
    
    # Store original port
    original_port = os.environ.get("REDIS_PORT", "6379")
    
    try:
        # Temporarily change Redis port to force failure
        os.environ["REDIS_PORT"] = "6380"  # Wrong port
        
        # Initialize cache - should fall back to in-memory
        initialize_litellm_cache()
        
        # Verify in-memory cache is configured
        assert litellm.cache is not None
        assert litellm.cache.type == "local"
    finally:
        # Reset Redis port
        os.environ["REDIS_PORT"] = original_port

def test_litellm_cache_completion():
    """Test cache functionality with completion call."""
    logger.info("Testing LiteLLM cache with completion")
    
    # Initialize with Redis cache
    initialize_litellm_cache()
    
    test_messages = [{"role": "user", "content": "Test message"}]
    
    # First call
    response1 = litellm.completion(
        model="gpt-4o-mini",
        messages=test_messages,
        cache={"no-cache": False}
    )
    
    # Second call should hit cache
    response2 = litellm.completion(
        model="gpt-4o-mini",
        messages=test_messages,
        cache={"no-cache": False}
    )
    
    assert response2._hidden_params.get("cache_hit") is True

def test_litellm_cache_operations():
    """Test basic LiteLLM cache operations."""
    logger.info("Testing LiteLLM cache operations")
    
    # Initialize cache
    initialize_litellm_cache()
    
    # Test direct Redis operations
    redis_client = redis.Redis(host="localhost", port=6379)
    
    # Test set and get
    key = "test_key"
    value = "test_value"
    redis_client.set(key, value)
    assert redis_client.get(key).decode() == value
    
    # Test delete
    redis_client.delete(key)
    assert redis_client.get(key) is None

def test_litellm_cache_error_handling():
    """Test LiteLLM cache error handling."""
    logger.info("Testing LiteLLM cache error handling")
    
    # Test with invalid Redis configuration
    with pytest.raises(redis.ConnectionError):
        redis.Redis(host="nonexistent", port=6379, socket_connect_timeout=1).ping() 