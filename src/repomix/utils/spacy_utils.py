import nltk
from nltk.tokenize import word_tokenize
from loguru import logger
from functools import lru_cache
import subprocess
import sys
from pathlib import Path
from typing import List

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


@lru_cache(maxsize=1)
def get_spacy_model(
    model_name: str = "en_core_web_sm",
    model_url: str = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0.tar.gz",
):
    """Get cached spaCy model. Download it if not already installed."""
    try:
        # Attempt to load the model
        return spacy.load(model_name)
    except OSError:
        # If the model is not found, download and install it
        logger.info(f"Model '{model_name}' not found. Attempting to install...")
        try:
            # Download and install the model using pip
            logger.info(f"Installing '{model_name}' model...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", model_url],
                check=True,
                capture_output=True,
                text=True
            )

            # Try loading the model again after installation
            logger.info(f"Model '{model_name}' installed successfully.")
            return spacy.load(model_name)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install '{model_name}': {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            raise


def split_text_into_chunks(text: str, chunk_size: int = 900000) -> List[str]:
    """Split text into chunks that are under spaCy's max_length limit."""
    # If text is under chunk_size, return as is
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    # Split by lines to avoid breaking in the middle of a line
    lines = text.split("\n")
    
    for line in lines:
        line_size = len(line) + 1  # +1 for the newline
        
        if current_size + line_size > chunk_size:
            # If current chunk has content, save it
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # If single line is bigger than chunk_size, split it
            if line_size > chunk_size:
                # Split the line into smaller pieces
                while line:
                    chunks.append(line[:chunk_size])
                    line = line[chunk_size:]
                continue
        
        current_chunk.append(line)
        current_size += line_size
    
    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks


def count_tokens(text: str) -> int:
    """Count tokens in text using NLTK, which handles large texts efficiently."""
    return len(word_tokenize(text))


def truncate_text_by_tokens(text: str, max_tokens: int = 50) -> str:
    """Truncate text to max_tokens while preserving meaning."""
    tokens = word_tokenize(text)
    
    if len(tokens) <= max_tokens:
        return text
        
    # Get first and last n/2 tokens
    half_tokens = max_tokens // 2
    start_tokens = tokens[:half_tokens]
    end_tokens = tokens[-half_tokens:]
    
    # Reconstruct text with ellipsis
    return " ".join(start_tokens) + "... " + " ".join(end_tokens)
