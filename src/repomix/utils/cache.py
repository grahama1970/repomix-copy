"""Cache and timing utilities for schema generator."""

import time
import sqlite3
import json
import zlib
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, Iterator, Generator, TypeVar, cast
from dataclasses import dataclass
from collections import defaultdict
from contextlib import contextmanager
from loguru import logger

# Get the schema_generator package root directory
PACKAGE_ROOT = Path(__file__).parent.parent

# Default compression settings
DEFAULT_COMPRESSION_LEVEL = 6
MIN_SIZE_FOR_COMPRESSION = 1024  # 1KB

T = TypeVar('T')

@dataclass
class TimingStats:
    """Container for timing statistics of schema operations."""
    operation: str
    total_time: float = 0.0
    calls: int = 0

    @property
    def average_time(self) -> float:
        """Calculate average operation time."""
        return self.total_time / self.calls if self.calls > 0 else 0.0


class TimingManager:
    """Manages timing statistics for schema generator operations."""

    def __init__(self) -> None:
        self.stats: Dict[str, TimingStats] = defaultdict(lambda: TimingStats(""))
        self.enabled = True

    @contextmanager
    def measure(self, operation: str, description: str = "") -> Generator[None, None, None]:
        """Context manager to measure execution time of an operation."""
        if not self.enabled:
            yield
            return

        start_time = time.time()
        try:
            if description:
                logger.debug(f"Starting {operation}: {description}")
            yield
        finally:
            elapsed = time.time() - start_time
            if operation not in self.stats:
                self.stats[operation] = TimingStats(operation)
            self.stats[operation].total_time += elapsed
            self.stats[operation].calls += 1
            if description:
                logger.debug(f"Completed {operation} in {elapsed:.2f}s")

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of timing statistics."""
        return {
            op: {
                "total_time": stat.total_time,
                "calls": stat.calls,
                "average_time": stat.average_time,
            }
            for op, stat in self.stats.items()
        }


class SchemaCache:
    """Persistent cache for schema analysis results using SQLite with compression."""

    def __init__(
        self,
        max_age_days: int = 30,
        max_size_mb: int = 100,
        compression_level: int = DEFAULT_COMPRESSION_LEVEL,
        cache_dir: Optional[Path] = None
    ) -> None:
        """Initialize the cache with cleanup and compression settings.

        Args:
            max_age_days: Maximum age of cache entries in days (default: 30)
            max_size_mb: Maximum size of cache in megabytes (default: 100)
            compression_level: zlib compression level 0-9 (default: 6)
            cache_dir: Optional custom cache directory
        """
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.compression_level = compression_level

        # Set up cache directory
        self.cache_dir = cache_dir or PACKAGE_ROOT / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "schema_analysis_cache.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_cache (
                    database_name TEXT,
                    collection_name TEXT,
                    analysis_type TEXT,
                    data BLOB,
                    schema_hash TEXT,
                    timestamp REAL,
                    size INTEGER,
                    compressed BOOLEAN,
                    PRIMARY KEY (database_name, collection_name, analysis_type)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON schema_cache(timestamp)"
            )

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        return zlib.compress(data, level=self.compression_level)

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress zlib compressed data."""
        return zlib.decompress(data)

    def _calculate_schema_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash of schema data to detect changes."""
        schema_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()

    def get(
        self, database: str, collection: str, analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached schema analysis if it exists and is valid."""
        self._cleanup_if_needed()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT data, compressed FROM schema_cache 
                    WHERE database_name = ? AND collection_name = ? AND analysis_type = ?
                    """,
                    (database, collection, analysis_type)
                ).fetchone()

                if row:
                    data, is_compressed = row
                    if is_compressed:
                        data = self._decompress_data(data)
                    return cast(Dict[str, Any], json.loads(data))
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None

    def set(
        self, database: str, collection: str, analysis_type: str, data: Dict[str, Any]
    ) -> None:
        """Cache schema analysis result with compression."""
        try:
            schema_hash = self._calculate_schema_hash(data)
            data_blob = json.dumps(data).encode()

            # Compress if the data is large enough
            should_compress = len(data_blob) > MIN_SIZE_FOR_COMPRESSION
            if should_compress:
                data_blob = self._compress_data(data_blob)

            size = len(data_blob)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO schema_cache 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        database,
                        collection,
                        analysis_type,
                        data_blob,
                        schema_hash,
                        time.time(),
                        size,
                        should_compress,
                    )
                )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    def _cleanup_if_needed(self) -> None:
        """Perform cache cleanup if size or age limits are exceeded."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check current cache size
                total_size = conn.execute(
                    "SELECT COALESCE(SUM(size), 0) FROM schema_cache"
                ).fetchone()[0]

                if total_size > self.max_size_mb * 1024 * 1024:
                    # Remove oldest entries until under size limit
                    conn.execute(
                        """
                        DELETE FROM schema_cache 
                        WHERE rowid IN (
                            SELECT rowid FROM schema_cache 
                            ORDER BY timestamp ASC 
                            LIMIT -1 OFFSET ?
                        )
                        """,
                        (self.max_size_mb * 1024 * 1024 // 1000,)
                    )

                # Remove expired entries
                max_age = time.time() - (self.max_age_days * 24 * 60 * 60)
                conn.execute(
                    "DELETE FROM schema_cache WHERE timestamp < ?",
                    (max_age,)
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache cleanup failed: {e}")

    def clear(self) -> None:
        """Clear the entire cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM schema_cache")
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache clear failed: {e}")

    def recompress_all(self, new_level: Optional[int] = None) -> Dict[str, Any]:
        """Recompress all cached data with new compression level."""
        if new_level is not None:
            self.compression_level = new_level

        stats = {
            "total": 0,
            "compressed": 0,
            "size_before": 0,
            "size_after": 0
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT database_name, collection_name, analysis_type, data, compressed 
                    FROM schema_cache
                    """
                ).fetchall()

                for db, coll, analysis_type, data, was_compressed in rows:
                    stats["total"] += 1
                    original_size = len(data)
                    stats["size_before"] += original_size

                    # Decompress if needed
                    if was_compressed:
                        data = self._decompress_data(data)

                    # Try to compress if large enough
                    if len(data) > MIN_SIZE_FOR_COMPRESSION:
                        compressed_data = self._compress_data(data)
                        new_size = len(compressed_data)
                        stats["size_after"] += new_size
                        stats["compressed"] += 1

                        conn.execute(
                            """
                            UPDATE schema_cache 
                            SET data = ?, size = ?, compressed = 1
                            WHERE database_name = ? AND collection_name = ? AND analysis_type = ?
                            """,
                            (compressed_data, new_size, db, coll, analysis_type)
                        )
                    else:
                        stats["size_after"] += len(data)

                conn.commit()
        except Exception as e:
            logger.error(f"Recompression failed: {e}")

        return stats


# Create global instances
timing = TimingManager()
schema_cache = SchemaCache() 