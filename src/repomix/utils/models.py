"""Models for repomix using Pydantic V2 patterns."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class Message(BaseModel):
    """Message for LLM conversation."""
    role: str
    content: str
    model_config = ConfigDict(frozen=True)


class TokenUsage(BaseModel):
    """Token usage statistics."""
    model_config = ConfigDict(frozen=True)
    
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


class LLMRequest(BaseModel):
    """Request to LLM API."""
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    model_config = ConfigDict(frozen=True)


class LLMResponse(BaseModel):
    """Structured LLM response with metadata and usage statistics."""
    model_config = ConfigDict(frozen=True)
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique response identifier"
    )
    response: str = Field(
        ...,
        description="Generated response content from the LLM",
        min_length=1
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata including model info and cache status"
    )
    usage: TokenUsage = Field(
        ...,
        description="Token usage statistics for the request and response"
    )


class MultiDirectoryResponse(BaseModel):
    """Container for multiple directory analysis results."""
    model_config = ConfigDict(frozen=True)
    
    repository: str = Field(..., description="Repository URL or path")
    directories: Dict[str, LLMResponse] = Field(
        default_factory=dict,
        description="Analysis results for each directory"
    )
    combined_tokens: int = Field(..., description="Total tokens processed")
    execution_time: float = Field(..., description="Total execution time in seconds")
    errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Any errors encountered during analysis"
    ) 