#!/usr/bin/env python3

"""
RepoConcatenator CLI - Analyze GitHub repositories with LLMs.

A tool to analyze GitHub repositories and local directories using LLMs.
Supports both single directory analysis and multi-directory analysis.

Usage:
    # Single directory analysis
    repomix ask path/to/repo "What does this code do?" --model gpt-4o-mini

    # Multiple directory analysis
    repomix analyze \\
        "@path/to/repo/dir1" \\
        "@path/to/repo/dir2" \\
        --model gpt-4o-mini \\
        --combined-analysis

For more information, run:
    repomix --help
    repomix ask --help
    repomix analyze --help
"""

import sys
from typing import Optional, List
from loguru import logger
from repomix.cli import cli

def main(args: Optional[List[str]] = None) -> None:
    """Entry point for the CLI with proper error handling.
    
    Args:
        args: Optional list of command line arguments. If None, sys.argv[1:] is used.
    """
    try:
        cli.main(args=args or sys.argv[1:])
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 