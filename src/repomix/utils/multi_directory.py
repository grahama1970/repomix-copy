"""Module for handling multi-directory analysis functionality."""
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from loguru import logger
from repomix.utils.file_operations import collect_files
from repomix.utils.parser import concatenate_files
from repomix.utils.llm import query_model
import litellm

async def validate_directories(directories: List[str]) -> List[Path]:
    """Validate that all provided directories exist.
    
    Args:
        directories: List of directory paths to validate.
        
    Returns:
        List of validated Path objects.
        
    Raises:
        ValueError: If any directory does not exist.
    """
    validated = []
    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            raise ValueError(f"Directory '{dir_path}' does not exist")
        if not path.is_dir():
            raise ValueError(f"'{dir_path}' is not a directory")
        validated.append(path)
    return validated

async def process_directory(directory: Path, repo_url: str = "", target_dir: str = "") -> Dict[str, Any]:
    """Process a single directory and prepare its content for analysis.
    
    Args:
        directory: Path to the directory to process.
        repo_url: Optional repository URL for context.
        target_dir: Optional target directory path for context.
        
    Returns:
        Dictionary containing the processed files and content.
    """
    logger.info(f"Processing directory: {directory}")
    
    # Collect files from the directory
    files = collect_files(directory)
    if not files:
        logger.warning(f"No files found in directory: {directory}")
        return {"files": [], "content": ""}
    
    # Concatenate files with context
    content = concatenate_files(files, directory, repo_url, target_dir)
    
    return {
        "files": [str(f) for f in files],
        "content": content
    }

async def combine_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine results from multiple directories.
    
    Args:
        results: List of directory processing results.
        
    Returns:
        Combined results dictionary.
    """
    combined_files = []
    combined_content = []
    
    for result in results:
        combined_files.extend(result["files"])
        if result["content"]:
            combined_content.append(result["content"])
    
    return {
        "files": combined_files,
        "content": "\n\n".join(combined_content)
    }

async def analyze_directories(
    directories: List[str],
    model: str,
    question: str,
    repo_url: str = "",
    target_dir: str = "",
    combined_analysis: bool = False
) -> Dict[str, Any]:
    """Analyze multiple directories concurrently.
    
    Args:
        directories: List of directory paths to analyze.
        model: Name of the model to use for analysis.
        question: Question to ask about the directories.
        repo_url: Optional repository URL for context.
        target_dir: Optional target directory path for context.
        combined_analysis: Whether to analyze all directories together.
        
    Returns:
        Dictionary containing analysis results.
        
    Raises:
        ValueError: If directories list is empty or contains invalid directories.
        litellm.NotFoundError: If the model is invalid.
        litellm.BadRequestError: If there's an issue with the model request.
    """
    # Validate input
    if not directories:
        logger.error("No directories provided for analysis")
        raise ValueError("Directory list cannot be empty")
        
    # Validate directories
    validated_dirs = await validate_directories(directories)
    logger.info(f"Validated directories: {[str(d) for d in validated_dirs]}")
    
    # Process each directory
    tasks = [process_directory(d, repo_url, target_dir) for d in validated_dirs]
    results = await asyncio.gather(*tasks)
    
    if combined_analysis:
        # Combine results and analyze together
        combined = await combine_results(results)
        system_prompt = f"Analyze these directories and answer: {question}"
        try:
            response = await query_model(model, combined["content"], system_prompt)
            return {
                "files": combined["files"],
                "analysis": response,
                "is_combined": True
            }
        except Exception as e:
            logger.error(f"Error querying model {model} for combined analysis: {type(e).__name__}: {str(e)}")
            logger.debug(f"Analysis context: combined_files={len(combined['files'])}, content_length={len(combined['content'])}")
            # Re-raise litellm exceptions directly
            if isinstance(e, litellm.exceptions.NotFoundError):
                logger.error(f"Invalid model: {model}")
                raise
            if isinstance(e, litellm.exceptions.BadRequestError):
                logger.error(f"Bad request to model {model}: {str(e)}")
                raise
            raise ValueError(f"Error with model {model}: {str(e)}")
    else:
        # Analyze each directory separately
        analysis_tasks = []
        for result in results:
            if result["content"]:
                system_prompt = f"Analyze this directory and answer: {question}"
                try:
                    task = query_model(model, result["content"], system_prompt)
                    analysis_tasks.append(task)
                except Exception as e:
                    logger.error(f"Error querying model {model} for directory analysis: {type(e).__name__}: {str(e)}")
                    logger.debug(f"Analysis context: files={len(result['files'])}, content_length={len(result['content'])}")
                    # Re-raise litellm exceptions directly
                    if isinstance(e, litellm.exceptions.NotFoundError):
                        logger.error(f"Invalid model: {model}")
                        raise
                    if isinstance(e, litellm.exceptions.BadRequestError):
                        logger.error(f"Bad request to model {model}: {str(e)}")
                        raise
                    raise ValueError(f"Error with model {model}: {str(e)}")
        
        try:
            analyses = await asyncio.gather(*analysis_tasks)
            return {
                "directory_results": [
                    {
                        "files": result["files"],
                        "analysis": analysis
                    }
                    for result, analysis in zip(results, analyses)
                    if result["content"] and analysis is not None
                ],
                "is_combined": False
            }
        except Exception as e:
            logger.error(f"Error during parallel analysis: {type(e).__name__}: {str(e)}")
            # Re-raise litellm exceptions directly
            if isinstance(e, litellm.exceptions.NotFoundError):
                logger.error(f"Invalid model: {model}")
                raise
            if isinstance(e, litellm.exceptions.BadRequestError):
                logger.error(f"Bad request to model {model}: {str(e)}")
                raise
            raise ValueError(f"Analysis failed: {str(e)}") 