#!/usr/bin/env python3

# Note: Pydantic deprecation warnings are from dependencies using older Pydantic patterns.
# These warnings can be safely ignored as they don't affect our code's functionality.
# Our own models use the recommended ConfigDict approach.

from typing import List, Optional, Tuple, Dict, Any
import click
from loguru import logger
from pathlib import Path
import asyncio
from functools import wraps
import time
import os
import sys
import json
from pydantic import BaseModel, ConfigDict, Field

from repomix.utils.git import parse_github_url, clone_repository, cleanup_repository, is_github_url, parse_multi_urls, clone_github_repo
from repomix.utils.analyzer import analyze_directory, analyze_directories_combined, analyze_single_directory, analyze_multiple_directories_combined
from repomix.utils.llm import query_model, LLMResponse
from repomix.utils.spacy_utils import count_tokens

# Configure loguru with structured logging and context
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "repomix_debug.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
    level="DEBUG",
    rotation="10 MB",
    retention="3 days",
    enqueue=True,  # Thread-safe logging
    backtrace=True,  # Detailed exception information
    diagnose=True   # Additional diagnostic info
)

DEFAULT_IGNORE_PATTERNS: List[str] = [
    # Version control
    ".git/*",
    ".gitignore",
    ".gitattributes",
    ".github/*",
    ".gitlab/*",
    ".svn/*",
    
    # IDE and editor files
    ".vscode/*",
    ".idea/*",
    ".vs/*",
    "*.swp",
    "*.swo",
    
    # Build and dependency directories
    "node_modules/*",
    "dist/*",
    "build/*",
    "target/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    
    # Package management
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    
    # Documentation
    "*.md",
    "*.rst",
    "*.txt",
    "docs/*",
    "doc/*",
    
    # Configuration files
    "*.json",
    "*.yaml",
    "*.yml",
    "*.toml",
    "*.ini",
    "*.cfg",
    "*.conf",
    
    # Data files
    "*.csv",
    "*.tsv",
    "*.xlsx",
    "*.xls",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    
    # Media files
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.mp3",
    "*.mp4",
    "*.wav",
    "*.avi",
    
    # Archive files
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    
    # Binary files
    "*.exe",
    "*.bin",
    "*.dat",
    
    # Log files
    "*.log",
    "logs/*",
    
    # Test files and directories
    "tests/*",
    "test/*",
    "*_test.go",
    "*_test.py",
    "*_test.js",
    "*_test.ts",
    "*_spec.rb",
    
    # Other
    ".DS_Store",
    "Thumbs.db"
]

class MultiDirectoryResponse(BaseModel):
    """Container for multiple directory analysis results."""
    repository: str
    directories: Dict[str, LLMResponse]
    combined_tokens: int
    execution_time: float
    errors: Dict[str, str] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=True)

@click.group()
def cli():
    """RepoConcatenator CLI - Analyze GitHub repositories with LLMs."""
    pass

def async_command(f):
    """Decorator to run async Click commands."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(f(*args, **kwargs))
    return wrapper

@cli.command()
@click.argument("repo_dir")
@click.argument("question")
@click.option("--model-id", required=True, help="LiteLLM model ID to use")
@click.option("--stream", is_flag=True, help="Stream the response")
@async_command
async def ask(repo_dir: str, question: str, model_id: str, stream: bool):
    """Ask a question about a repository or directory."""
    click.echo(f"Starting analysis of repository: {repo_dir}", err=True)
    click.echo(f"Question: {question}", err=True)
    click.echo(f"Using model: {model_id}", err=True)

    try:
        # Check if directory exists before proceeding
        if not os.path.exists(repo_dir):
            logger.error(f"Directory not found: {repo_dir}")
            raise click.ClickException(f"Directory '{repo_dir}' does not exist")

        # Clone repository if it's a GitHub URL
        repo_path = repo_dir
        if is_github_url(repo_dir):
            click.echo(f"Cloning GitHub repository: {repo_dir}", err=True)
            repo_path = await clone_github_repo(repo_dir)
            click.echo(f"Repository cloned to: {repo_path}", err=True)

        # Process directory
        response = await query_model(
            model=model_id,
            content=f"Analyze this repository and answer: {question}\n\nRepository: {repo_path}",
            system_prompt="You are a helpful assistant analyzing code repositories.",
            stream=stream
        )

        if stream and hasattr(response, "__aiter__"):
            # Handle streaming response
            async for chunk in response:
                if isinstance(chunk, str):
                    click.echo(chunk, nl=False)
                else:
                    click.echo(chunk.choices[0].delta.content or "", nl=False)
            click.echo()  # Final newline
        else:
            # Handle non-streaming response
            if isinstance(response, str):
                click.echo(response)
            elif hasattr(response, "response"):
                click.echo(response.response)
                click.echo(f"Response tokens: {response.usage.total_tokens}", err=True)
                click.echo(f"\nTokens used: {response.usage.total_tokens}")

    except Exception as e:
        logger.error("Fatal error during processing", exc_info=True)
        raise click.ClickException(str(e))

@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--model-id', required=True, help='LiteLLM model ID to use')
@click.option('--output-dir', default='output', help='Output directory for analysis results')
@click.option('--ignore-patterns', multiple=True, help='Patterns to ignore during analysis')
@click.option('--system-prompt', help='Custom system prompt for the LLM')
@click.option('--max-tokens', type=int, help='Maximum tokens for LLM response')
@click.option('--combined-analysis', is_flag=True, help='Analyze all directories together')
@async_command
async def analyze(urls: Tuple[str, ...], model_id: str, output_dir: str,
           ignore_patterns: Tuple[str, ...], system_prompt: Optional[str],
           max_tokens: Optional[int], combined_analysis: bool):
    """Analyze GitHub repositories or local directories.

    URLS can be GitHub repository URLs or local directory paths, prefixed with @.
    Example: repomix analyze @path/to/repo1 @path/to/repo2 --model-id openai/gpt-4
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Convert ignore_patterns tuple to list
        ignore_list = list(ignore_patterns) if ignore_patterns else None

        # Process directories
        total_tokens = 0
        start_time = time.time()

        # Parse URLs and get repository info
        multi_info = parse_multi_urls(list(urls))
        click.echo(f"Processing repository: {multi_info.repo_url}", err=True)
        click.echo(f"Branch: {multi_info.branch}", err=True)
        click.echo(f"Directories to process: {len(multi_info.target_dirs)}", err=True)

        # Check if any URL is a GitHub URL
        has_github_url = any(url.startswith('https://github.com/') for url in urls)

        if has_github_url:
            # Clone repository
            repo_dir = await clone_github_repo(multi_info.repo_url)
            try:
                if combined_analysis:
                    click.echo("Using combined analysis", err=True)
                    tokens = await analyze_directories_combined(
                        [Path(repo_dir) / d for d in multi_info.target_dirs],
                        output_dir,
                        model_id,
                        ignore_list,
                        system_prompt,
                        max_tokens
                    )
                    total_tokens += tokens
                else:
                    for target_dir in multi_info.target_dirs:
                        dir_path = Path(repo_dir) / target_dir
                        if not dir_path.exists():
                            click.echo(f"Directory not found: {dir_path}", err=True)
                            continue
                        tokens = await analyze_directory(
                            dir_path,
                            output_dir,
                            model_id,
                            ignore_list,
                            system_prompt,
                            max_tokens
                        )
                        total_tokens += tokens
            finally:
                # Clean up cloned repository
                cleanup_repository(repo_dir)
        else:
            # Process local directories
            dirs_to_analyze = [Path(url.lstrip('@')) for url in urls]
            
            if combined_analysis:
                # Verify all directories exist
                click.echo("Using combined analysis", err=True)
                existing_dirs = [d for d in dirs_to_analyze if d.exists()]
                if not existing_dirs:
                    raise click.ClickException("No valid directories found")
                
                tokens = await analyze_directories_combined(
                    existing_dirs,
                    output_dir,
                    model_id,
                    ignore_list,
                    system_prompt,
                    max_tokens
                )
                total_tokens += tokens
            else:
                for dir_path in dirs_to_analyze:
                    if not dir_path.exists():
                        click.echo(f"Directory not found: {dir_path}", err=True)
                        continue
                    tokens = await analyze_directory(
                        dir_path,
                        output_dir,
                        model_id,
                        ignore_list,
                        system_prompt,
                        max_tokens
                    )
                    total_tokens += tokens

        execution_time = time.time() - start_time
        click.echo(f"\nAnalysis completed in {execution_time:.2f} seconds")
        click.echo(f"Total tokens processed: {total_tokens}")
        click.echo(f"Results saved in: {output_dir}")

    except Exception as e:
        logger.error(f"Error analyzing directories: {str(e)}")
        raise click.ClickException(str(e))

def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main() 