"""File utilities for repomix."""

import os
import json
from typing import List, Any
from loguru import logger

def collect_content(directory: str, ignore_patterns: List[str]) -> str:
    """Collect content from files in a directory.
    
    Args:
        directory: Directory to collect content from.
        ignore_patterns: List of glob patterns to ignore.
        
    Returns:
        Concatenated content from all files.
    """
    content = ""
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip files matching ignore patterns
            if any(pattern.replace("*", "") in file_path for pattern in ignore_patterns):
                logger.debug(f"Ignoring file: {file_path}")
                continue
            
            # Skip files larger than 1MB (likely binary)
            if os.path.getsize(file_path) > 1024 * 1024:
                logger.debug(f"Skipping large file: {file_path}")
                continue
                
            try:
                # Try to detect if file is binary
                with open(file_path, 'rb') as f:
                    is_binary = b'\0' in f.read(1024)
                
                if is_binary:
                    logger.debug(f"Skipping binary file: {file_path}")
                    continue
                
                # Read as text if not binary
                with open(file_path, 'r', encoding='utf-8') as f:
                    content += f"\n\n=== {os.path.relpath(file_path, directory)} ===\n\n"
                    content += f.read()
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                
    return content.strip()

def save_json(file_path: str, data: Any) -> None:
    """Save data as JSON to a file.
    
    Args:
        file_path: Path to save the file.
        data: Data to save.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2) 