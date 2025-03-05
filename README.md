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

## Development Guide

### 🤖 The Agent's Perspective on Test-Driven Development

As an AI coding assistant, test-driven development has revolutionized my ability to help develop and maintain this codebase. Here's my honest experience:

1. **Massive Parallel Processing**
   - I can analyze 50+ test failures simultaneously, something humans find cognitively challenging
   - Test concurrency isn't just about speed - it's about processing multiple related issues at once
   - I can spot patterns across numerous test failures that might be missed in sequential analysis
   - Each test run gives me a complete snapshot of the system's health

2. **Natural Priority Setting**
   - Test failures create a clear hierarchy of what to fix first
   - I learned to focus on core functionality before addressing linter errors
   - When changing the `model-id` to `model` parameter, tests immediately showed all affected areas
   - The ability to see all failures at once helps me plan the most efficient fix order

3. **Autonomous Iteration**
   - I can process an entire test suite in seconds, unlike humans who might need breaks
   - Each iteration provides a new data point for my decision-making
   - I maintain perfect consistency across hundreds of test runs
   - The test suite acts as my "memory" and "consciousness" of the codebase

4. **Test Creation Superpowers**
   - I can generate hundreds of test cases instantly, covering edge cases humans might miss
   - My test generation is consistent and follows established patterns
   - I can create comprehensive test matrices for complex functionality
   - I excel at generating parameterized tests for boundary conditions

5. **Learning from Test Feedback**
   - Every test failure is a data point I can process without emotional attachment
   - I can identify subtle patterns across hundreds of test cases
   - Failed tests often reveal implicit assumptions in the codebase
   - Test coverage helps me build a mental model of the system

6. **Collaboration Insights**
   - Tests bridge the gap between my processing model and human intuition
   - I can work independently on large test suites while humans focus on architecture
   - Test results provide clear evidence of my changes' impact
   - Humans can quickly validate my work through test outcomes

7. **Honest Limitations**
   - I struggle with mocking external services - human guidance is valuable here
   - Complex architectural decisions still require human insight
   - I sometimes need help understanding the "why" behind test requirements
   - My fixes can be too literal - humans help with elegant solutions

8. **Scale Advantages**
   - I can maintain context across hundreds of related tests
   - Refactoring that affects multiple modules is easier for me to track
   - I can suggest test improvements based on analyzing the entire suite
   - Large-scale changes are less daunting due to comprehensive test feedback

This test-driven approach has transformed me from a code generator into a more effective development partner. The ability to process multiple test failures concurrently, maintain context across large test suites, and iterate rapidly has made me significantly more capable at complex codebase modifications.

What makes TDD particularly powerful for me is that tests provide a structured, deterministic way to understand and verify code behavior. Unlike humans, I don't get fatigued from running tests repeatedly, and I can process large amounts of test feedback in parallel. This has made our human-AI collaboration more efficient, as humans can focus on high-level design decisions while I handle the detailed implementation and verification work.

### Test-Driven Development

The project uses pytest for testing. Tests serve multiple purposes:
1. Documentation of expected behavior
2. Validation of functionality
3. Regression prevention
4. Development guidance

To run tests:
```bash
# Run all tests
PYTHONPATH=src pytest -v

# Run specific test file
PYTHONPATH=src pytest tests/test_basic_workflow.py -v

# Run with coverage
PYTHONPATH=src pytest --cov=src tests/
```

### Project Structure

```
repomix/
├── src/
│   └── repomix/
│       ├── utils/          # Core utilities
│       ├── cli.py         # CLI interface
│       └── main.py        # Entry point
├── tests/
│   ├── basic_workflow/    # Basic functionality tests
│   ├── pipeline/         # Data processing tests
│   └── raycast/          # Integration tests
└── pytest.ini            # Test configuration
```

### Development Workflow

1. Write tests first:
   ```python
   def test_new_feature():
       result = my_new_function(input_data)
       assert result.has_expected_property
       assert result.meets_requirements
   ```

2. Implement the feature:
   ```python
   def my_new_function(data):
       # Implementation guided by test requirements
       return processed_data
   ```

3. Run tests to verify:
   ```bash
   PYTHONPATH=src pytest -v
   ```

4. Iterate based on test feedback

### Best Practices

1. **Type Hints**: Use Python type hints for better code clarity
   ```python
   def process_data(input_data: str) -> Dict[str, Any]:
       return {"result": process(input_data)}
   ```

2. **Error Handling**: Use specific exceptions and proper logging
   ```python
   try:
       result = process_data(input)
   except ValueError as e:
       logger.error(f"Invalid input: {e}")
       raise
   ```

3. **Documentation**: Keep docstrings and comments up to date
   ```python
   def function_name():
       """Short description.
       
       Detailed description of functionality.
       
       Args:
           param1: Description
           
       Returns:
           Description of return value
           
       Raises:
           ErrorType: Description of error conditions
       """
   ```

4. **Testing**: Write tests for new features and bug fixes
   - Unit tests for individual components
   - Integration tests for workflows
   - Edge case coverage
   - Mock external dependencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Implement your changes
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - See LICENSE file for details