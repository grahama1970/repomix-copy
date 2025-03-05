"""LLM integration using LiteLLM with Redis caching."""

import os
import uuid
from typing import Union, AsyncGenerator, Optional, Any
import redis
import litellm
from loguru import logger

from repomix.utils.models import LLMResponse, TokenUsage

def initialize_litellm_cache():
    try:
        logger.debug("Starting LiteLLM cache initialization...")
        # Test Redis connection
        test_redis = redis.Redis(
            host="localhost", port=6379, password=None, socket_timeout=2
        )
        if not test_redis.ping():
            raise ConnectionError("Redis is not responding.")

        # Log existing keys
        keys = test_redis.keys("*")
        if keys:
            logger.debug(f"Existing Redis keys: {keys}")

        # Configure cache
        litellm.cache = litellm.Cache(
            type="redis",
            host="localhost",
            port=6379,
            password=None,
            supported_call_types=["acompletion", "completion"],
            ttl=60 * 60 * 24 * 2  # 2 days
        )
        litellm.enable_cache()
        os.environ["LITELLM_LOG"] = "DEBUG"

    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
        litellm.cache = litellm.Cache(type="local")
        litellm.enable_cache()

async def query_model(
    model: str = "openai/gpt-4o-mini",
    content: str = "",
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    stream: bool = False,
    max_retries: int = 3
) -> Union[LLMResponse, AsyncGenerator[str, None]]:
    """Query LLM model with proper error handling and response typing."""
    try:
        messages = [
            {"role": "system", "content": system_prompt or "You are a helpful AI assistant."},
            {"role": "user", "content": content}
        ]

        completion_kwargs = {
            "model": model,
            "messages": messages,
            "max_retries": max_retries,
            "stream": stream
        }
        
        if max_tokens is not None:
            completion_kwargs["max_tokens"] = max_tokens

        if stream:
            return litellm.acompletion(**completion_kwargs)
        
        response = await litellm.acompletion(**completion_kwargs)

        return LLMResponse(
            id=response.id,
            response=response.choices[0].message.content,
            metadata={
                "model": response.model,
                "request_id": str(uuid.uuid4()),
                "cache_hit": getattr(response, "cache_hit", False)
            },
            usage=TokenUsage(
                completion_tokens=response.usage.completion_tokens,
                prompt_tokens=response.usage.prompt_tokens,
                total_tokens=response.usage.total_tokens
            )
        )

    except Exception as e:
        logger.error(f"Error querying model {model}: {type(e).__name__}: {str(e)}")
        logger.debug(f"Query details: content_length={len(content)}, max_tokens={max_tokens}, stream={stream}")
        if isinstance(e, litellm.exceptions.NotFoundError):
            logger.error(f"Invalid model ID: {model}")
        elif isinstance(e, litellm.exceptions.BadRequestError):
            logger.error(f"Bad request to model {model}: {str(e)}")
        raise

def save_response(response: LLMResponse, path: str) -> None:
    """Save LLM response to file with proper validation."""
    try:
        with open(path, "w") as f:
            f.write(response.model_dump_json(indent=2))
        logger.debug(f"Response saved to {path}")
    except Exception as e:
        logger.error(f"Error saving response: {e}")
        raise 