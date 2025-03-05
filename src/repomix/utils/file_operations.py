"""File operations utilities for repomix."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from loguru import logger
import mimetypes

def read_file(file_path: Union[str, Path]) -> str:
    """Read a file and return its contents as a string."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

def write_file(file_path: Union[str, Path], content: str) -> None:
    """Write content to a file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise

def save_json(file_path: Union[str, Path], data: Any) -> None:
    """Save data as JSON to a file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        raise

def load_json(file_path: Union[str, Path]) -> Any:
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        raise

def collect_files(
    directory: Union[str, Path],
    ignore_patterns: Optional[List[str]] = None
) -> List[Path]:
    """Collect all files in a directory, respecting ignore patterns."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = Path(root) / filename
            if ignore_patterns and any(file_path.match(pattern) for pattern in ignore_patterns):
                continue
            files.append(file_path)
    return files

def ensure_directory(directory: Union[str, Path]) -> Path:
    """Ensure a directory exists and return its Path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)

def is_binary_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is binary using both MIME type and content analysis.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if the file is binary, False if it's text
        
    The function uses two methods to detect binary files:
    1. MIME type detection based on file extension
    2. Null byte detection in the first 1024 bytes
    
    A file is considered binary if either:
    - Its MIME type doesn't start with 'text/'
    - It contains null bytes in its content
    """
    try:
        # First check MIME type
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

def get_file_extension(file_path: Union[str, Path]) -> str:
    """Get file extension without the dot."""
    """Get file extension (lowercase, without dot)."""
    return os.path.splitext(str(file_path))[1].lower().lstrip('.')

def is_text_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is a text file based on extension and content."""
    # Common text file extensions
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

def clean_directory(directory: Union[str, Path]) -> None:
    """Remove all files and subdirectories in a directory."""
    directory = Path(directory)
    if directory.exists():
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                clean_directory(item)
                item.rmdir()
        directory.rmdir()  # Remove the directory itself 