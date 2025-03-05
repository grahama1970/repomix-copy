"""File parsing and concatenation utilities for repomix."""
from typing import List, Dict, Any
from pathlib import Path
import glob
from datetime import datetime
import tiktoken
from loguru import logger
import mimetypes
from repomix.utils.spacy_utils import count_tokens
from repomix.utils.file_operations import is_binary_file


def glob_files(
    base_path: Path,
    target_dir: str,
    ignore_patterns: List[str],
    allow_missing: bool = False
) -> List[Path]:
    """
    Find all files in target directory excluding ignored patterns.
    
    Args:
        base_path: Base repository path
        target_dir: Target directory within repository
        ignore_patterns: List of glob patterns to ignore
        allow_missing: If True, return empty list for missing directories
        
    Returns:
        List of paths to matching files
    """
    target_path = base_path / target_dir.lstrip('/')
    if not target_path.exists():
        if allow_missing:
            return []
        raise ValueError(f"Target directory not found: {target_path}")
        
    files = []
    for file in target_path.rglob('*'):
        if not file.is_file():
            continue
            
        # Skip ignored files
        if any(file.match(pattern) for pattern in ignore_patterns):
            continue
            
        # Skip binary files
        if is_binary_file(file):
            continue
            
        files.append(file)
                
    return files


def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: Input text
        
    Returns:
        Number of tokens
    """
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))


def generate_metadata(
    files: List[Path],
    total_tokens: int,
    repo_url: str,
    target_dir: str
) -> Dict[str, Any]:
    """
    Generate metadata for concatenated file.
    
    Args:
        files: List of processed files
        total_tokens: Total token count
        repo_url: Repository URL
        target_dir: Target directory
        
    Returns:
        Dictionary of metadata
    """
    return {
        "total_tokens": total_tokens,
        "file_count": len(files),
        "repository": repo_url,
        "target_directory": target_dir,
        "generated": datetime.now().isoformat()
    }


def concatenate_files(
    files: List[Path],
    base_path: Path,
    repository_url: str,
    target_dir: str
) -> str:
    """
    Concatenate files with metadata.
    
    Args:
        files: List of files to concatenate
        base_path: Base repository path
        repository_url: URL of the repository
        target_dir: Target directory within repository
        
    Returns:
        Concatenated file content with metadata
    """
    if not files:
        return ""
        
    # Build metadata section
    metadata = {
        "total_tokens": 0,  # Will be updated by LLM
        "file_count": len(files),
        "repository": repository_url,
        "target_directory": target_dir,
        "generated": datetime.now().isoformat()
    }
    
    # Build metadata section
    result = ["# Metadata"]
    for key, value in metadata.items():
        result.append(f"{key}: {value}")
    
    # Add files with proper separation
    for file in files:
        # Skip binary files
        if is_binary_file(file):
            logger.debug(f"Skipping binary file: {file}")
            continue
            
        try:
            relative_path = str(file.relative_to(base_path))
            content = file.read_text()  # Preserve exact file content
            
            # Add empty line before file section (except first file)
            if len(result) > 0:
                result.append("")
                
            # Add file header and content
            result.append(f"File: {relative_path}")
            result.append(content)
        except UnicodeDecodeError:
            logger.debug(f"Skipping file with encoding issues: {file}")
            continue
    
    return "\n".join(result)


def format_file_section(filepath: str, content: str) -> str:
    """Format a file section with proper header."""
    return f"File: {filepath}\n{content}"


def split_long_line(line: str, filename: str, part_number: int, token_limit: int) -> List[str]:
    """Split a long line into multiple chunks that fit within token limit."""
    print(f"DEBUG: split_long_line called with line length {len(line)}, token_limit {token_limit}")
    line_chunks: List[str] = []
    remaining = line
    
    while remaining:
        prefix = f"{part_number:03d}"
        header = format_file_section(f"{prefix}_{filename}", "")
        available_tokens = token_limit - count_tokens(header)
        print(f"DEBUG: Available tokens after header: {available_tokens}")
        
        # Take as much of the line as possible while staying under the token limit
        current_part = remaining
        while count_tokens(current_part) > available_tokens:
            # Binary search to find the largest substring that fits
            left, right = 0, len(current_part)
            while left < right - 1:
                mid = (left + right) // 2
                if count_tokens(current_part[:mid]) <= available_tokens:
                    left = mid
                else:
                    right = mid
            current_part = current_part[:left]
            print(f"DEBUG: Binary search found part length {len(current_part)}")
            
            # Ensure we make progress
            if not current_part:
                current_part = remaining[:max(1, len(remaining) // 2)]
                print(f"DEBUG: Empty part, forcing progress with length {len(current_part)}")
                break
        
        chunk = format_file_section(f"{prefix}_{filename}", current_part)
        print(f"DEBUG: Created chunk with {count_tokens(chunk)} tokens")
        line_chunks.append(chunk)
        remaining = remaining[len(current_part):]
        part_number += 1
        print(f"DEBUG: Remaining length: {len(remaining)}")
        
        # Safety check to prevent infinite loops
        if len(remaining) == len(line):
            print("DEBUG: No progress made, forcing advancement")
            remaining = remaining[1:]  # Force progress
    
    return line_chunks


def chunk_content(content_by_file: Dict[str, str], token_limit: int = 4000) -> List[str]:
    """
    Splits repository text into chunks within the token limit.
    
    For each file:
      - If any line in the file exceeds the token limit, that line is split first
      - If the file (header + content) fits within the token limit, it is added as a whole
      - Otherwise, the file is split line by line into parts
    """
    chunks: List[str] = []
    current_chunk = ""
    current_chunk_tokens = 0
    
    def flush_current_chunk() -> None:
        nonlocal current_chunk, current_chunk_tokens
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            current_chunk = ""
            current_chunk_tokens = 0
    
    # Process files in sorted order for deterministic output
    for filename in sorted(content_by_file.keys()):
        content = content_by_file[filename]
        lines = content.split("\n")
        
        # First check if any individual line exceeds the token limit
        has_long_lines = False
        for line in lines:
            header = format_file_section(filename, "")
            line_tokens = count_tokens(line)
            header_tokens = count_tokens(header)
            print(f"DEBUG: Line length: {len(line)} chars, {line_tokens} tokens")
            print(f"DEBUG: Header length: {len(header)} chars, {header_tokens} tokens")
            if line_tokens > (token_limit - header_tokens):
                has_long_lines = True
                print(f"DEBUG: Found long line: {line_tokens} tokens > {token_limit - header_tokens} available tokens")
                break
        
        if has_long_lines:
            print("DEBUG: Processing file with long lines")
            # Process the file line by line since we know some lines need splitting
            part_number = 1
            part_lines: List[str] = []
            current_part_tokens = 0
            
            for line in lines:
                header = format_file_section(f"{part_number:03d}_{filename}", "")
                header_tokens = count_tokens(header)
                line_tokens = count_tokens(line)
                
                if line_tokens > (token_limit - header_tokens):
                    print(f"DEBUG: Splitting line with {line_tokens} tokens")
                    # Flush any accumulated lines before handling the long line
                    if part_lines:
                        part_content = "\n".join(part_lines)
                        flush_current_chunk()
                        chunks.append(format_file_section(f"{part_number:03d}_{filename}", part_content))
                        part_number += 1
                        part_lines = []
                        current_part_tokens = 0
                    
                    # Split the long line
                    line_chunks = split_long_line(line, filename, part_number, token_limit)
                    print(f"DEBUG: Split into {len(line_chunks)} chunks")
                    chunks.extend(line_chunks)
                    part_number += len(line_chunks)
                else:
                    # Try to add line to current part
                    if current_part_tokens + line_tokens + header_tokens <= token_limit:
                        part_lines.append(line)
                        current_part_tokens += line_tokens
                    else:
                        # Current part is full, flush it
                        if part_lines:
                            part_content = "\n".join(part_lines)
                            flush_current_chunk()
                            chunks.append(format_file_section(f"{part_number:03d}_{filename}", part_content))
                            part_number += 1
                            part_lines = [line]
                            current_part_tokens = line_tokens
                        else:
                            # Single line becomes its own part
                            flush_current_chunk()
                            chunks.append(format_file_section(f"{part_number:03d}_{filename}", line))
                            part_number += 1
            
            # Flush any remaining lines
            if part_lines:
                part_content = "\n".join(part_lines)
                flush_current_chunk()
                chunks.append(format_file_section(f"{part_number:03d}_{filename}", part_content))
        else:
            # Try to add the whole file as one chunk
            full_section = format_file_section(filename, content)
            section_tokens = count_tokens(full_section)
            
            if section_tokens <= token_limit:
                # Try to append to current chunk if possible
                if current_chunk:
                    candidate = current_chunk + "\n\n" + full_section
                    candidate_tokens = count_tokens(candidate)
                    if candidate_tokens <= token_limit:
                        current_chunk = candidate
                        current_chunk_tokens = candidate_tokens
                        continue
                    else:
                        flush_current_chunk()
                current_chunk = full_section
                current_chunk_tokens = section_tokens
            else:
                # Split by lines (but we know no individual line exceeds the limit)
                part_number = 1
                part_lines = []
                current_part_tokens = 0
                
                for line in lines:
                    header = format_file_section(f"{part_number:03d}_{filename}", "")
                    header_tokens = count_tokens(header)
                    line_tokens = count_tokens(line)
                    
                    if current_part_tokens + line_tokens + header_tokens <= token_limit:
                        part_lines.append(line)
                        current_part_tokens += line_tokens
                    else:
                        # Flush current part
                        if part_lines:
                            part_content = "\n".join(part_lines)
                            flush_current_chunk()
                            chunks.append(format_file_section(f"{part_number:03d}_{filename}", part_content))
                            part_number += 1
                            part_lines = [line]
                            current_part_tokens = line_tokens
                        else:
                            # Single line becomes its own part
                            flush_current_chunk()
                            chunks.append(format_file_section(f"{part_number:03d}_{filename}", line))
                            part_number += 1
                
                # Flush any remaining lines
                if part_lines:
                    part_content = "\n".join(part_lines)
                    flush_current_chunk()
                    chunks.append(format_file_section(f"{part_number:03d}_{filename}", part_content))
    
    flush_current_chunk()
    return chunks 