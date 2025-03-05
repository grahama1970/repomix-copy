"""Git utilities for repomix."""

import os
import re
import tempfile
from pathlib import Path
from typing import Tuple, Optional, List
from loguru import logger
import subprocess
import click
from git import Repo
from dataclasses import dataclass
import asyncio

@dataclass
class RepoInfo:
    """Information about a repository and its target directories."""
    repo_url: str
    branch: str
    target_dirs: List[str]

def parse_github_url(url: str) -> Tuple[str, Optional[str], str]:
    """Parse a GitHub repository URL or local path into components.
    
    Args:
        url: GitHub repository URL or local path
        
    Returns:
        Tuple of (repository URL or local path, branch, target directory)
        
    Example:
        >>> parse_github_url("https://github.com/user/repo/tree/master/dir")
        ("https://github.com/user/repo", "master", "/dir")
        >>> parse_github_url("/local/path/to/dir")
        ("/local/path/to/dir", None, "")
    """
    try:
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Check if it's a local path
        if not url.startswith('https://github.com/'):
            path = Path(url)
            return str(path), None, ""
            
        # Extract parts for GitHub URL
        parts = url.split('/')
        
        if len(parts) < 5:
            raise ValueError("Invalid GitHub URL format")
            
        # Get repo URL
        repo_url = '/'.join(parts[:5])
        
        # Get branch and target directory
        branch = None
        target_dir = ''
        
        if len(parts) > 5:
            if parts[5] == 'tree':
                if len(parts) < 7:
                    raise ValueError("Invalid tree URL format")
                branch = parts[6]
                target_dir = '/' + '/'.join(parts[7:]) if len(parts) > 7 else ''
            else:
                target_dir = '/' + '/'.join(parts[5:])
                
        return repo_url, branch, target_dir
        
    except Exception as e:
        logger.error(f"Error parsing URL or path: {e}")
        raise ValueError(f"Invalid URL or path: {url}") from e

def clone_repository(repo_url: str, branch: str) -> Path:
    """Clone a GitHub repository to a temporary directory.
    
    Args:
        repo_url: GitHub repository URL
        branch: Branch to clone
        
    Returns:
        Path to the cloned repository
        
    Raises:
        click.ClickException: If cloning fails
    """
    # Create a unique temporary directory
    repo_dir = Path(tempfile.mkdtemp(prefix="repomix_"))
    
    try:
        logger.info(f"Cloning {repo_url} ({branch}) to {repo_dir}")
        subprocess.run(
            ["git", "clone", "-b", branch, "--depth", "1", repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True
        )
        return repo_dir
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr}")
        cleanup_repository(repo_dir)  # Clean up on failure
        raise click.ClickException(f"Failed to clone repository: {e.stderr}")

def cleanup_repository(repo_dir: Path) -> None:
    """Clean up a cloned repository.
    
    Args:
        repo_dir: Path to the repository directory
    """
    try:
        logger.info(f"Cleaning up repository at {repo_dir}")
        if repo_dir.exists():
            subprocess.run(
                ["rm", "-rf", str(repo_dir)],
                check=True,
                capture_output=True,
                text=True
            )
    except subprocess.CalledProcessError as e:
        logger.warning(f"Cleanup failed: {e.stderr}")

def is_github_url(url: str) -> bool:
    """Check if a string is a GitHub URL."""
    github_pattern = r"^@?https?://github\.com/[^/]+/[^/]+(/.*)?$"
    return bool(re.match(github_pattern, url))

def parse_multi_urls(urls: List[str]) -> RepoInfo:
    """Parse multiple GitHub URLs or directory paths.

    Args:
        urls: List of GitHub URLs or directory paths, optionally prefixed with @.

    Returns:
        RepoInfo containing repository URL, branch, and target directories.

    Raises:
        ValueError: If URLs are inconsistent or invalid.
    """
    if not urls:
        raise ValueError("No URLs provided")

    # Strip @ prefix if present
    cleaned_urls = [url[1:] if url.startswith('@') else url for url in urls]

    # Check if all URLs are GitHub URLs
    is_github = all(url.startswith('https://github.com/') for url in cleaned_urls)
    is_local = all(not url.startswith('https://github.com/') for url in cleaned_urls)

    if not (is_github or is_local):
        raise ValueError("All URLs must be from the same repository")

    if is_github:
        # Extract repository URL and branch from the first URL
        first_url = cleaned_urls[0]
        parts = first_url.split('/tree/')
        if len(parts) != 2:
            raise ValueError("Invalid GitHub URL format")
        
        repo_url = parts[0]
        branch_and_path = parts[1].split('/', 1)
        branch = branch_and_path[0]
        
        # Validate all URLs have the same repository and branch
        for url in cleaned_urls[1:]:
            parts = url.split('/tree/')
            if len(parts) != 2:
                raise ValueError("Invalid GitHub URL format")
            
            curr_repo = parts[0]
            curr_branch = parts[1].split('/', 1)[0]
            
            if curr_repo != repo_url:
                raise ValueError("All URLs must be from the same repository")
            if curr_branch != branch:
                raise ValueError("All URLs must use the same branch")
        
        # Extract target directories
        target_dirs = [url.split('/tree/')[1].split('/', 1)[1] for url in cleaned_urls]
    else:
        # Handle local paths
        paths = [Path(url) for url in cleaned_urls]
        
        # For single path, use the parent directory as repo_url
        if len(paths) == 1:
            path = paths[0]
            if path.is_absolute():
                repo_url = str(path.parent)
                target_dirs = [path.name]
            else:
                parts = str(path).split('/', 1)
                repo_url = parts[0]
                target_dirs = [parts[1]] if len(parts) > 1 else ['.']
        else:
            # Find the common parent directory
            common_parent = os.path.commonpath([str(p) for p in paths])
            if not common_parent or common_parent == '.':
                # If no common parent, use the first directory as repo_url
                parts = str(paths[0]).split('/', 1)
                repo_url = parts[0]
                target_dirs = [str(Path(url).relative_to(repo_url)) for url in cleaned_urls]
            else:
                repo_url = common_parent
                target_dirs = [str(Path(url).relative_to(common_parent)) for url in cleaned_urls]
        
        branch = "master"  # Default branch for local paths

    return RepoInfo(
        repo_url=repo_url,
        branch=branch,
        target_dirs=target_dirs
    )

async def clone_github_repo(url: str) -> str:
    """Clone a GitHub repository to a temporary directory.
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Path to cloned repository
        
    Raises:
        ValueError: If URL is invalid or clone fails
    """
    clone_url = parse_github_url(url)[0]  # Get just the repo URL
    temp_dir = tempfile.mkdtemp(prefix="repomix_")
    
    try:
        # Run git clone in a subprocess to avoid blocking
        process = await asyncio.create_subprocess_exec(
            "git", "clone", clone_url, temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Git clone failed: {stderr.decode()}")
            
        return temp_dir
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise ValueError(f"Failed to clone repository: {e}") 