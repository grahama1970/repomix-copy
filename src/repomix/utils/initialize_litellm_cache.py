import litellm
import os
import redis
from loguru import logger
from repomix.utils.file_utils import load_env_file

load_env_file()


def initialize_litellm_cache():
    try:
        logger.debug("Starting LiteLLM cache initialization...")

        # Test Redis connection before enabling caching
        logger.debug("Testing Redis connection...")
        test_redis = redis.Redis(
            host="localhost", port=6379, password=None, socket_timeout=2
        )
        if not test_redis.ping():
            raise ConnectionError("Redis is not responding.")

        # Verify Redis is empty or log existing keys
        keys = test_redis.keys("*")
        if keys:
            logger.debug(f"Existing Redis keys: {keys}")
        else:
            logger.debug("Redis cache is empty")

        # Set up LiteLLM cache with debug logging
        logger.debug("Configuring LiteLLM Redis cache...")
        litellm.cache = litellm.Cache(
            type="redis",
            host="localhost",  # Redis host
            port=6379,  # Redis port
            password=None,  # Password if set, otherwise None
            supported_call_types=["acompletion", "completion"],
            ttl=60 * 60 * 24 * 2,  # 2 days
        )

        # Enable caching and verify
        logger.debug("Enabling LiteLLM cache...")
        litellm.enable_cache()

        # Set debug logging for LiteLLM
        os.environ["LITELLM_LOG"] = "DEBUG"

        # Verify cache configuration
        logger.debug(
            f"LiteLLM cache config: {litellm.cache.__dict__ if hasattr(litellm.cache, '__dict__') else 'No cache config available'}"
        )
        logger.info("✅ Redis caching enabled on localhost:6379")

        # Try a test set/get to verify Redis is working
        try:
            test_key = "litellm_cache_test"
            test_redis.set(test_key, "test_value", ex=60)
            result = test_redis.get(test_key)
            logger.debug(f"Redis test write/read successful: {result == b'test_value'}")
            test_redis.delete(test_key)
        except Exception as e:
            logger.warning(f"Redis test write/read failed: {e}")

    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(
            f"⚠️ Redis connection failed: {e}. Falling back to in-memory caching."
        )
        # Fall back to in-memory caching if Redis is unavailable
        logger.debug("Configuring in-memory cache fallback...")
        litellm.cache = litellm.Cache(type="local")
        litellm.enable_cache()
        logger.debug("In-memory cache enabled")


def test_litellm_cache():
    """Test the LiteLLM cache functionality with a sample completion call"""
    initialize_litellm_cache()

    try:
        # Test the cache with a simple completion call
        test_messages = [
            {"role": "user", "content": "What is the capital of France?"}
        ]  # Make sure it's >1024 tokens
        logger.info("Testing cache with completion call...")

        # First call should miss cache
        response1 = litellm.completion(
            model="gpt-4o-mini",
            messages=test_messages,
            cache={"no-cache": False},
        )
        logger.info(f"First call usage: {response1.usage}")
        if m := response1._hidden_params.get("cache_hit"):
            logger.info(f"Response 1: Cache hit: {m}")

        # Second call should hit cache
        response2 = litellm.completion(
            model="gpt-4o-mini",
            messages=test_messages,
            cache={"no-cache": False},
        )
        logger.info(f"Second call usage: {response2.usage}")
        if m := response2._hidden_params.get("cache_hit"):
            logger.info(f"Response 2: Cache hit: {m}")

    except Exception as e:
        logger.error(f"Cache test failed with error: {e}")
        raise


if __name__ == "__main__":
    test_litellm_cache()
