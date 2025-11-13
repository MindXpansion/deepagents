"""SQLite database for research history management."""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ResearchDatabase:
    """Manages research history storage and retrieval."""

    def __init__(self, db_path: str = "research_history.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create research table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    query TEXT NOT NULL,
                    report TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on symbol for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol
                ON research(symbol)
            """)

            # Create index on created_at for timeline queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON research(created_at DESC)
            """)

            conn.commit()
            logger.info("Database initialized successfully")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def save_research(
        self,
        symbol: str,
        query: str,
        report: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Save research report to database.

        Args:
            symbol: Stock ticker symbol
            query: Original research query
            report: Generated research report
            metadata: Optional metadata (data used, tool calls, etc.)

        Returns:
            ID of saved research record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO research (symbol, query, report, metadata)
                VALUES (?, ?, ?, ?)
            """, (symbol.upper(), query, report, metadata_json))

            conn.commit()
            research_id = cursor.lastrowid

            logger.info(f"Saved research for {symbol} with ID {research_id}")
            return research_id

    def get_research_by_id(self, research_id: int) -> Optional[Dict]:
        """
        Retrieve research by ID.

        Args:
            research_id: Research record ID

        Returns:
            Dictionary with research data or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, symbol, query, report, metadata, created_at
                FROM research
                WHERE id = ?
            """, (research_id,))

            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def get_research_by_symbol(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get research history for a symbol.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of records to return

        Returns:
            List of research records, newest first
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, symbol, query, report, metadata, created_at
                FROM research
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (symbol.upper(), limit))

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_recent_research(self, limit: int = 20) -> List[Dict]:
        """
        Get most recent research records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of research records, newest first
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, symbol, query, report, metadata, created_at
                FROM research
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def search_research(self, search_term: str, limit: int = 20) -> List[Dict]:
        """
        Search research by query or report content.

        Args:
            search_term: Term to search for
            limit: Maximum number of records to return

        Returns:
            List of matching research records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            search_pattern = f"%{search_term}%"

            cursor.execute("""
                SELECT id, symbol, query, report, metadata, created_at
                FROM research
                WHERE query LIKE ? OR report LIKE ? OR symbol LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_symbols_list(self) -> List[str]:
        """
        Get list of all unique symbols in database.

        Returns:
            List of stock symbols
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT symbol
                FROM research
                ORDER BY symbol
            """)

            return [row[0] for row in cursor.fetchall()]

    def get_research_count(self) -> int:
        """
        Get total number of research records.

        Returns:
            Count of research records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM research")
            return cursor.fetchone()[0]

    def delete_research(self, research_id: int) -> bool:
        """
        Delete research record by ID.

        Args:
            research_id: Research record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM research WHERE id = ?", (research_id,))
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted research ID {research_id}")
            return deleted

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """
        Convert database row to dictionary.

        Args:
            row: SQLite row object

        Returns:
            Dictionary representation
        """
        data = {
            "id": row["id"],
            "symbol": row["symbol"],
            "query": row["query"],
            "report": row["report"],
            "created_at": row["created_at"]
        }

        # Parse metadata if present
        if row["metadata"]:
            try:
                data["metadata"] = json.loads(row["metadata"])
            except json.JSONDecodeError:
                data["metadata"] = None

        return data


# Global database instance
_db_instance = None


def get_database() -> ResearchDatabase:
    """
    Get global database instance (singleton pattern).

    Returns:
        ResearchDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = ResearchDatabase()
    return _db_instance
