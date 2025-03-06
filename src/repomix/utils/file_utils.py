"""Unified file utilities for repomix.

This module provides a comprehensive set of file operations utilities:
1. Project configuration (root detection, env loading)
2. File operations (read, write, collect)
3. JSON handling
4. Directory operations
5. File type detection
"""

import os
import json
import mimetypes
from pathlib import Path
from typing import Union, Optional, List, Any
from loguru import logger
from dotenv import load_dotenv

# Project Configuration
def get_project_root(marker_file: str = ".git") -> Path:
    """Find the project root directory by looking for a marker file.

    Args:
        marker_file (str): File/directory to look for (default: ".git")

    Returns:
        Path: Project root directory path

    Raises:
        RuntimeError: If marker file not found in parent directories
    """
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.root:
        if (current_dir / marker_file).exists():
            return current_dir
        current_dir = current_dir.parent
    raise RuntimeError(f"Could not find project root. Ensure {marker_file} exists.")

def load_env_file(env_name: Optional[str] = None) -> None:
    """Load environment variables from a .env file.

    Args:
        env_name (str, optional): Environment name suffix to look for.
            If provided, looks for .env.{env_name}. Otherwise looks for .env

    Raises:
        FileNotFoundError: If .env file not found in expected locations
    """
    project_dir = get_project_root()
    env_dirs = [project_dir, project_dir / "app/backend"]

    for env_dir in env_dirs:
        env_file = env_dir / (f".env.{env_name}" if env_name else ".env")
        if env_file.exists():
            load_dotenv(env_file)
            return

    raise FileNotFoundError(
        f"Environment file {'.env.' + env_name if env_name else '.env'} "
        f"not found in any known locations."
    )

# File Operations
def read_file(file_path: Union[str, Path]) -> str:
    """Read a file and return its contents as a string.
    
    Args:
        file_path: Path to the file to read

    Returns:
        str: Content of the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there are issues reading the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.debug(f"Successfully read file: {file_path} (size: {len(content)} bytes)")
            return content
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except IOError as e:
        logger.error(f"IOError while reading file {file_path}: {str(e)}")
        raise IOError(f"Error reading file {file_path}: {str(e)}") from e
    except Exception as e:
        logger.critical(f"Unexpected error reading file {file_path}: {str(e)}")
        raise

def write_file(file_path: Union[str, Path], content: str) -> None:
    """Write content to a file.
    
    Args:
        file_path: Path where to write the file
        content: Content to write

    Raises:
        IOError: If there are issues writing the file
    """
    try:
        os.makedirs(os.path.dirname(str(file_path)), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            logger.debug(f"Successfully wrote file: {file_path}")
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise

# JSON Operations
def save_json(file_path: Union[str, Path], data: Any) -> None:
    """Save data as JSON to a file.
    
    Args:
        file_path: Path where to save the JSON file
        data: Data to serialize to JSON

    Raises:
        IOError: If there are issues writing the file
        JSONDecodeError: If data cannot be serialized to JSON
    """
    try:
        os.makedirs(os.path.dirname(str(file_path)), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Successfully saved JSON to: {file_path}")
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        raise

def load_json(file_path: Union[str, Path]) -> Any:
    """Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file

    Returns:
        Any: Parsed JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Successfully loaded JSON from: {file_path}")
            return data
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        raise

# Directory Operations
def collect_files(
    directory: Union[str, Path],
    ignore_patterns: Optional[List[str]] = None
) -> List[Path]:
    """Collect all files in a directory, respecting ignore patterns.
    
    Args:
        directory: Directory to scan
        ignore_patterns: List of glob patterns to ignore

    Returns:
        List[Path]: List of file paths found

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = Path(root) / filename
            if ignore_patterns and any(file_path.match(pattern) for pattern in ignore_patterns):
                logger.debug(f"Ignoring file: {file_path}")
                continue
            files.append(file_path)
    return files

def collect_content(directory: Union[str, Path], ignore_patterns: List[str]) -> str:
    """Collect and concatenate content from all text files in a directory.
    
    Args:
        directory: Directory to collect content from
        ignore_patterns: List of glob patterns to ignore

    Returns:
        str: Concatenated content from all text files
    """
    content = ""
    directory = Path(directory)
    
    for file_path in collect_files(directory, ignore_patterns):
        # Skip large or binary files
        if file_path.stat().st_size > 1024 * 1024 or is_binary_file(file_path):
            logger.debug(f"Skipping large or binary file: {file_path}")
            continue
            
        try:
            file_content = read_file(file_path)
            content += f"\n\n=== {file_path.relative_to(directory)} ===\n\n"
            content += file_content
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
                
    return content.strip()

def clean_directory(directory: Union[str, Path]) -> None:
    """Remove all files and subdirectories in a directory.
    
    Args:
        directory: Directory to clean

    Note:
        This operation is recursive and will remove the directory itself.
    """
    directory = Path(directory)
    if directory.exists():
        # First remove all files
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
                
        # Then recursively handle subdirectories
        for item in directory.iterdir():
            if item.is_dir():
                clean_directory(item)
                
        # Finally remove the directory itself
        directory.rmdir()

# File Type Detection
def get_file_extension(file_path: Union[str, Path]) -> str:
    """Get file extension (lowercase, without dot)."""
    return os.path.splitext(str(file_path))[1].lower().lstrip('.')

def is_binary_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is binary using MIME type and content analysis.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if the file is binary, False if it's text
    """
    try:
        # Check MIME type first
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not mime_type.startswith('text/'):
            return True
            
        # Then check for null bytes
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception as e:
        logger.warning(f"Error checking if file is binary {file_path}: {e}")
        return True  # Assume binary if we can't read the file

def is_text_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is a text file based on extension and content.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if the file is text, False if it's binary
    """
    text_extensions = {
        'txt', 'md', 'py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'hpp',
        'css', 'html', 'xml', 'json', 'yaml', 'yml', 'ini', 'conf',
        'sh', 'bash', 'zsh', 'fish', 'bat', 'ps1', 'rb', 'php', 'go',
        'rs', 'scala', 'kt', 'kts', 'swift', 'r', 'pl', 'pm', 'sql'
    }
    
    extension = get_file_extension(file_path)
    if extension in text_extensions:
        return True
        
    # For unknown extensions, check content
    return not is_binary_file(file_path)

if __name__ == "__main__":
    load_env_file()
    print(os.getenv("OPENAI_API_KEY"))
