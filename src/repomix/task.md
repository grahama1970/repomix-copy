# RepoConcatenator Task

⚠️ **IMPLEMENTATION NOTE**
- The code examples in this document are VERIFIED WORKING implementations
- DO NOT modify these patterns unless you have a specific bug to fix
- Especially preserve:
  1. The exact Redis cache initialization code
  2. The LLMResponse model structure
  3. The query_model function signature and types
  4. The save_response implementation

## Overview
Analyze any GitHub directory with a single command. Just copy-paste a URL.

## Usage
```bash
# Single directory analysis
repomix ask path/to/repo "What does this code do?" --model-id gpt-4o-mini

# Multiple directory analysis
repomix analyze \\
    "@path/to/repo/dir1" \\
    "@path/to/repo/dir2" \\
    --model-id gpt-4o-mini \\
    --combined-analysis
```

That's it! The tool will:
1. Find all relevant code files
2. Analyze them using a suitable LLM
3. Give you insights about the code

## Core Requirements

### Model Configuration
- Use "gpt-4o-mini" as the default model ID
- Support both streaming and non-streaming responses
- Handle model-specific token limits
- Implement proper error handling for model responses

### File Concatenation Format
The tool's core functionality relies on a standardized file concatenation format:

```
File: {relative_path_from_repo_root}
{file_content}

```

Requirements:
1. Each file section starts with "File: " and the relative path
2. Paths MUST:
   - Use forward slashes (/)
   - Start from the repository root
   - Not start with a leading slash
   - Preserve the exact case of the original path
3. Original file content MUST be preserved exactly
4. Two newlines MUST separate different files

Example:
```
File: commands/browsing/open-chrome.js
// Original content here
console.log('example');

File: commands/browsing/clear-history.js
// Another file content
function clearHistory() {
  // ...
}
```

This format ensures:
- Consistent processing across all repository types
- Clear file boundaries for LLM analysis
- Preserved file structure context
- Reliable content extraction

## Features

### Single-URL Interface
- Just paste any GitHub URL you're looking at
- Works with:
  ```
  ✓ Directory URLs (github.com/user/repo/tree/...)
  ✓ Repository URLs (github.com/user/repo)
  ✓ Branch URLs   (github.com/user/repo/tree/branch)
  ```

### Smart Defaults
- Automatically detects what to analyze
- Skips non-code files (images, binaries, etc)
- Uses appropriate LLM model
- Saves results in convenient location

### Clean Output
```
Analysis Results
---------------
Found: 15 script files in browsing/
Summary: Collection of browser automation scripts for:
- URL management
- Window handling
- Privacy features
...
```

## Implementation Details
```
src/repomix/
├── data/           # Output directory for concatenated files
├── utils/
│   ├── git.py      # Git operations
│   ├── parser.py   # File parsing and concatenation
│   ├── models.py   # Pydantic data models
│   └── llm.py      # LiteLLM integration with caching
└── main.py         # CLI and main logic
```

## Implementation Steps
1. Set up Click CLI interface
2. Implement URL parsing and validation
3. Create Git clone/cleanup utilities
4. Develop file globbing and concatenation
5. Add token counting and metadata generation
6. Integrate LiteLLM API calls with:
   - Redis caching configuration:
     ```python
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
     ```
   - Local fallback for Redis failures
   - Structured request/response models
   - Streaming support
   - Retry handling with exponential backoff
7. Add error handling and logging
8. Implement cleanup procedures

## Error Handling
- Invalid repository URLs
- Network connectivity issues
- File permission problems
- Invalid glob patterns
- LiteLLM API errors
- Token limit exceeded
- Redis connection failures
- Cache initialization errors
- Temporary directory cleanup failures

## Testing
- Focus on user scenarios:
  - Various GitHub URL formats users might paste
  - Different repository structures
  - Error cases with clear messages
- Integration tests:
  - End-to-end workflow with parallel execution
  - Error handling and retries
  - Response formatting and validation
  - Cache hit/miss scenarios
- Format validation:
  - Correct file paths in concatenated output
  - Proper file separation
  - Content preservation
  - Standard format compliance
  - Structured response validation
  - Token usage tracking

### Async Testing and Click Integration
Key implementation patterns for async Click commands:

1. **Click Command Decoration**
   ```python
   @cli.command()
   @click.argument("repo_dir", type=click.Path(exists=True))
   @async_command  # Must be the innermost decorator
   async def command_name(...):
       # Async implementation
   ```

2. **Event Loop Management**
   - Use a single event loop at the entry point
   - Let Click's command invocation handle the loop
   - Avoid nested event loops or multiple `asyncio.run()` calls
   - The `@async_command` decorator manages event loops for Click commands

3. **Testing Async Commands**
   - Use `CliRunner` for Click command testing
   - No need to await `runner.invoke()` - it handles async internally
   - Example:
   ```python
   def test_async_command(tmp_path):
       runner = CliRunner()
       result = runner.invoke(cli, ["command", "--arg", "value"])
       assert result.exit_code == 0
   ```

4. **Model Testing**
   - Use real LiteLLM model IDs in tests (e.g., "openai/gpt-4")
   - Avoid mocking unless absolutely necessary
   - Test both streaming and non-streaming responses
   - Handle API errors and retries in tests

5. **Common Pitfalls to Avoid**
   - Don't use `asyncio.run()` inside Click commands
   - Don't nest async functions inside sync Click commands
   - Don't await `CliRunner.invoke()` in tests
   - Don't mix sync and async contexts unnecessarily

## Response Format
The tool provides structured responses using Pydantic V2 models:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any

class TokenUsage(BaseModel):
    """Token usage statistics."""
    model_config = ConfigDict(frozen=True)
    
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

class LLMResponse(BaseModel):
    """Structured LLM response with metadata and usage statistics."""
    model_config = ConfigDict(frozen=True)
    
    id: str = Field(
        ...,
        description="Unique response identifier from the LLM provider",
        min_length=1
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
```

This ensures:
- Consistent response format with validation
- Immutable responses (frozen config using ConfigDict)
- Proper error handling with field constraints
- Token usage tracking with structured data
- Cache status monitoring in metadata
- Request/response correlation via unique IDs
- Safe handling of mutable defaults using Field.default_factory

### Important Implementation Notes:
1. Always use `ConfigDict` for model configuration (Pydantic V2)
2. Use `Field.default_factory` for mutable defaults (lists, dicts)
3. Consider making models immutable with `frozen=True`
4. Validate field constraints using Field parameters
5. Keep models focused and composable
6. Use type hints consistently

### Response Handling
The tool supports both streaming and non-streaming responses:
```python
# Non-streaming response: Returns LLMResponse
response = await query_model(model="gpt-4o-mini", content="...", system_prompt="...")

# Streaming response: Returns AsyncGenerator[str, None]
async for chunk in query_model(model="gpt-4o-mini", content="...", system_prompt="...", stream=True):
    print(chunk)
```

When saving responses:
```python
# For non-streaming responses
save_response(response: LLMResponse, path: Path)

# For streaming, collect chunks first
chunks = [chunk async for chunk in streaming_response]
combined_response = LLMResponse(...)  # Construct from chunks
save_response(combined_response, path)
```

## Multiple Directory Support
The tool supports analyzing multiple directories from the same repository concurrently:

### Usage
```bash
# Analyze multiple directories with @ prefix
repomix "@https://github.com/raycast/script-commands/tree/master/commands/browsing" \
        "@https://github.com/raycast/script-commands/tree/master/commands/dashboard" \
        "@https://github.com/raycast/script-commands/tree/master/commands/math"
```

### Implementation Strategy

1. **URL Processing**
   - URLs prefixed with @ are treated as part of a multi-directory analysis
   - Non-prefixed URLs are treated as single directory analysis (backward compatibility)
   - URLs must be from the same repository to optimize cloning

2. **Concurrent Processing**
   ```python
   async def process_directories(
       repo_url: str,
       directories: List[str],
       model_id: str,
       **kwargs
   ) -> List[LLMResponse]:
       """Process multiple directories concurrently."""
       tasks = []
       for directory in directories:
           tasks.append(analyze_directory(repo_url, directory, model_id, **kwargs))
       return await asyncio.gather(*tasks)
   ```

3. **Repository Optimization**
   - Clone repository once for all directories
   - Share the same repository instance across tasks
   - Clean up only after all directories are processed

4. **Output Organization**
   ```
   data/
   ├── browsing/
   │   ├── concatenated.txt
   │   └── response.json
   ├── dashboard/
   │   ├── concatenated.txt
   │   └── response.json
   └── math/
       ├── concatenated.txt
       └── response.json
   ```