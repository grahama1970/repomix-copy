"""Repository analysis utilities."""
from typing import Dict, List, Optional, Tuple, Any, Union, AsyncGenerator
from pathlib import Path
import os
import uuid
from loguru import logger
from repomix.utils.parser import glob_files, concatenate_files, chunk_content
from repomix.utils.spacy_utils import count_tokens, truncate_text_by_tokens
from repomix.utils.llm import query_model, LLMResponse, TokenUsage
from repomix.utils.file_operations import collect_files, save_json, read_file

def get_file_content(files: List[Path]) -> str:
    """Get concatenated content from a list of files."""
    content_parts = []
    for file_path in files:
        try:
            content = read_file(file_path)
            content_parts.append(f"File: {file_path}\n{content}\n")
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            continue
    return "\n".join(content_parts)

async def analyze_single_directory(
    repo_dir: Path,
    target_dir: str,
    model_id: str,
    ignore_patterns: List[str],
    system_prompt: Optional[str],
    max_tokens: int
) -> Tuple[str, Optional[LLMResponse], Optional[str]]:
    """Analyze a single directory and return its content and response."""
    try:
        files = glob_files(repo_dir, target_dir, ignore_patterns)
        if not files:
            return target_dir, None, "No files found matching criteria"
            
        content = concatenate_files(files, repo_dir, str(repo_dir), target_dir)
        total_tokens = count_tokens(content)
        
        if total_tokens > max_tokens:
            content = truncate_text_by_tokens(content, max_tokens)
            logger.warning(f"{target_dir}: Truncated content from {total_tokens} to {max_tokens} tokens")
            
        response = await query_model(
            model=model_id,
            content=content,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
        # Cast the response to handle both LLMResponse and AsyncGenerator
        if isinstance(response, AsyncGenerator):
            logger.warning("Streaming responses not yet supported for directory analysis")
            return target_dir, None, "Streaming responses not supported"
        return target_dir, response, None
        
    except Exception as e:
        return target_dir, None, str(e)

async def analyze_multiple_directories_combined(
    repo_dir: str,
    directories: List[str],
    model_id: str,
    ignore_patterns: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Analyze multiple directories together."""
    results: List[Dict[str, Any]] = []
    total_tokens = 0

    # Log token count for each directory
    for directory in directories:
        full_dir_path = os.path.join(repo_dir, directory)
        files = collect_files(full_dir_path, ignore_patterns or [])
        if not files:
            continue
        content = get_file_content(files)
        token_count = count_tokens(content)
        total_tokens += token_count
        logger.info(f"Directory {directory}: {token_count} tokens")

    # If total tokens exceed max context size, analyze directories individually
    max_context_size = 6000
    if total_tokens > max_context_size:
        logger.warning(f"Total content ({total_tokens} tokens) exceeds maximum context size ({max_context_size})")
        logger.info("Analyzing directories individually")
        
        combined_results: List[Dict[str, Any]] = []
        for directory in directories:
            full_dir_path = os.path.join(repo_dir, directory)
            files = collect_files(full_dir_path, ignore_patterns or [])
            if not files:
                continue
            
            content = get_file_content(files)
            response = await query_model(
                model=model_id,
                content=content,
                system_prompt=system_prompt,
                max_tokens=max_tokens
            )
            
            # Handle streaming responses
            if isinstance(response, AsyncGenerator):
                logger.warning(f"Streaming response not supported for directory {directory}")
                continue
                
            combined_results.append({
                "directory": directory,
                "analysis": response.response,
                "tokens": response.usage.total_tokens
            })
        
        # Create a combined response
        combined_response = LLMResponse(
            id=str(uuid.uuid4()),
            response="\n\n".join([
                f"Analysis for {result['directory']}:\n{result['analysis']}"
                for result in combined_results
            ]),
            metadata={
                "model": model_id,
                "analysis_type": "combined",
                "directories": directories,
                "total_tokens": total_tokens,
            },
            usage=TokenUsage(
                prompt_tokens=sum(int(result['tokens']) for result in combined_results),
                completion_tokens=0,
                total_tokens=sum(int(result['tokens']) for result in combined_results)
            )
        )
        
        return {
            "combined": combined_response,
            "total_tokens": total_tokens
        }
    
    # If total tokens are within limit, analyze all directories together
    all_content = []
    for directory in directories:
        full_dir_path = os.path.join(repo_dir, directory)
        files = collect_files(full_dir_path, ignore_patterns or [])
        if files:
            content = get_file_content(files)
            all_content.append(f"Content for {directory}:\n{content}")
    
    combined_content = "\n\n".join(all_content)
    try:
        response = await query_model(
            model=model_id,
            content=combined_content,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
        
        # Handle streaming responses
        if isinstance(response, AsyncGenerator):
            logger.warning("Streaming response not supported for combined analysis")
            return {
                "combined": None,
                "total_tokens": total_tokens
            }
            
        return {
            "combined": response,
            "total_tokens": total_tokens
        }
    except Exception as e:
        logger.error(f"Error during combined analysis: {e}")
        raise

async def analyze_directory(
    dir_path: Path,
    output_dir: str,
    model_id: str,
    ignore_patterns: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> int:
    """Analyze a single directory and save results.
    
    Args:
        dir_path: Path to directory to analyze
        output_dir: Directory to save results
        model_id: Model ID to use
        ignore_patterns: Patterns to ignore
        system_prompt: System prompt for model
        max_tokens: Maximum tokens for response
        
    Returns:
        Number of tokens processed
    """
    _, response, error = await analyze_single_directory(
        dir_path.parent,
        dir_path.name,
        model_id,
        ignore_patterns or [],
        system_prompt,
        max_tokens or 4000
    )
    
    if error:
        logger.error(f"Error analyzing {dir_path}: {error}")
        return 0
        
    if response:
        output_file = os.path.join(output_dir, f"{dir_path.name}_analysis.json")
        save_json(output_file, response.model_dump())
        return response.usage.total_tokens
        
    return 0

async def analyze_directories_combined(
    dirs: List[Path],
    output_dir: str,
    model_id: str,
    ignore_patterns: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> int:
    """Analyze multiple directories together and save results.
    
    Args:
        dirs: List of directory paths
        output_dir: Directory to save results
        model_id: Model ID to use
        ignore_patterns: Patterns to ignore
        system_prompt: System prompt for model
        max_tokens: Maximum tokens for response
        
    Returns:
        Number of tokens processed
    """
    # Find common parent
    common_parent = os.path.commonpath([str(d) for d in dirs])
    relative_dirs = [str(d.relative_to(common_parent)) for d in dirs]
    
    result = await analyze_multiple_directories_combined(
        common_parent,
        relative_dirs,
        model_id,
        ignore_patterns,
        system_prompt,
        max_tokens
    )
    
    if result["combined"]:
        output_file = os.path.join(output_dir, "combined_analysis.json")
        save_json(output_file, result["combined"].model_dump())
        
    return int(result["total_tokens"]) 