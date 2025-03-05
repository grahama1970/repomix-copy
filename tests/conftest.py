"""Configure pytest for repomix tests."""
import pytest
import os
import tempfile
from pathlib import Path
from loguru import logger
import sys
import warnings

# Filter Pydantic deprecation warnings
warnings.filterwarnings(
    "ignore",
    message="Support for class-based.*",
    category=DeprecationWarning,
    module="pydantic.*"
)
warnings.filterwarnings(
    "ignore",
    message=".*config.* is deprecated.*",
    category=DeprecationWarning,
    module="pydantic.*"
)

# Configure test logging
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level> | {extra}"

@pytest.fixture(autouse=True)
def setup_logging(request):
    """Configure logging for tests with file and console output."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("tests/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a log file named after the test
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    log_file = logs_dir / f"{test_name}.log"
    
    # Remove existing handlers
    logger.remove()
    
    # Add handlers for both file and console
    logger.add(
        log_file,
        format=LOG_FORMAT,
        level="DEBUG",
        rotation="1 MB",
        retention="3 days",
        enqueue=True
    )
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level="INFO",
        enqueue=True
    )
    
    # Add test context
    logger.configure(
        extra={
            "test_name": test_name,
            "test_path": str(request.path)
        }
    )
    
    yield
    
    # Clean up
    logger.info(f"Test logs saved to: {log_file}")

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    files = {
        "test1.py": "print('Hello')\n",
        "test2.py": "def add(a, b):\n    return a + b\n",
        "test3.txt": "Sample text file\n",
        "subdir/test4.py": "class Test:\n    pass\n"
    }
    
    for path, content in files.items():
        file_path = temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    
    return temp_dir

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis for testing cache operations."""
    mock = mocker.patch("redis.Redis")
    mock.return_value.ping.return_value = True
    mock.return_value.keys.return_value = []
    mock.return_value.scan_iter.return_value = []
    mock.return_value.info.return_value = {"used_memory_human": "1M"}
    return mock

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    ) 