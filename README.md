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

```bash
python repomix_v2.py --repo /path/to/repo [OPTIONS]
```

### Options

- `--repo PATH`: Path to repository directory (required)
- `--include PATTERN`: Glob pattern for files to include (default: *)
- `--exclude PATTERN`: Comma-separated glob patterns for files to exclude
- `--depth NUMBER`: Maximum depth of child directories to include
- `--output FILE`: Output JSON file name (default: output.json)

### Example

```bash
python repomix_v2.py --repo ./my-project --include "*.py,*.js" --exclude "tests/*,*.pyc" --depth 2 --output repo_contents.json
```

## Output Format

The tool generates a JSON file with the following structure:

```json
{
  "repository": "/path/to/repo",
  "include_pattern": "*.py,*.js",
  "exclude_pattern": "tests/*,*.pyc",
  "depth": 2,
  "total_token_count": 1234,
  "files": [
    {
      "path": "file1.py",
      "content": "...",
      "token_count": 567
    },
    {
      "path": "file2.js",
      "content": "...",
      "token_count": 890
    }
  ]
}
```

## Logging

Logs are written to `repomix.log` with rotation at 10MB. 