# Repomix v2

A Python tool for processing repository contents with token counting capabilities.

## Features

- Process repository files with include/exclude patterns
- Count tokens using tiktoken (compatible with GPT models)
- Generate JSON output with file contents and token counts
- Configurable directory depth
- Detailed logging

## Installation

1. Clone this repository
2. Install dependencies using `uv`:
```bash
uv pip install -r requirements.txt
```

## Usage

### Basic Repository Analysis
```bash
# Analyze a GitHub repository directory
repomix ask https://github.com/raycast/script-commands/tree/master/commands/browsing \
    "What do these scripts do?" \
    --model openai/gpt-4o-mini

# Analyze a local directory
repomix ask ./my-project \
    "Explain the main functionality of this code" \
    --model openai/gpt-4o-mini \
    --stream  # Optional: stream the response in real-time
```

### Example Output
```json
{
  "id": "resp-2024-03-05-123456",
  "response": "These scripts are a collection of Raycast browser automation commands that:\n1. Manage browser windows and tabs\n2. Handle bookmarks and history\n3. Provide privacy features like clearing data\n4. Automate common browsing tasks",
  "metadata": {
    "model": "openai/gpt-4o-mini",
    "request_id": "req-abc-123",
    "cache_hit": false
  },
  "usage": {
    "completion_tokens": 128,
    "prompt_tokens": 512,
    "total_tokens": 640
  }
}
```

### Multiple Directory Analysis
```bash
# Note: Use @ prefix for paths in analyze command
repomix analyze \
    @https://github.com/raycast/script-commands/tree/master/commands/browsing \
    @https://github.com/raycast/script-commands/tree/master/commands/developer-utils \
    --model openai/gpt-4o-mini \
    --combined-analysis

# Local directories also need @ prefix
repomix analyze \
    @./project/src \
    @./project/tests \
    --model openai/gpt-4o-mini \
    --combined-analysis
```

### Advanced Options

For both `ask` and `analyze` commands:
- `--model`: LLM model name with provider prefix (e.g., openai/gpt-4, anthropic/claude-3)
- `--stream`: Stream the response in real-time (ask command only)
- `--output-dir`: Specify output directory (default: output/)
- `--ignore-patterns`: Patterns to ignore (e.g., "*.pyc,*.log")
- `--system-prompt`: Custom system prompt for the LLM
- `--max-tokens`: Maximum tokens for LLM response

### Legacy File Processing
```