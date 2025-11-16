"""Unit tests for database functionality."""

import pytest
import sys
import tempfile
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.utils.database import ResearchDatabase


class TestResearchDatabase:
    """Test research database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        # Create temp file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Create database
        db = ResearchDatabase(db_path=path)

        yield db

        # Cleanup
        try:
            os.unlink(path)
        except:
            pass

    def test_database_initialization(self, temp_db):
        """Test database initializes correctly."""
        assert temp_db is not None
        assert temp_db.get_research_count() == 0

    def test_save_and_retrieve_research(self, temp_db):
        """Test saving and retrieving research."""
        # Save research
        research_id = temp_db.save_research(
            symbol="AAPL",
            query="Analyze Apple stock",
            report="Test report content",
            metadata={"test": "data"}
        )

        assert research_id > 0

        # Retrieve research
        research = temp_db.get_research_by_id(research_id)

        assert research is not None
        assert research["symbol"] == "AAPL"
        assert research["query"] == "Analyze Apple stock"
        assert research["report"] == "Test report content"
        assert research["metadata"]["test"] == "data"

    def test_get_research_by_symbol(self, temp_db):
        """Test retrieving research by symbol."""
        # Save multiple research items
        temp_db.save_research("AAPL", "Query 1", "Report 1")
        temp_db.save_research("AAPL", "Query 2", "Report 2")
        temp_db.save_research("MSFT", "Query 3", "Report 3")

        # Get AAPL research
        aapl_research = temp_db.get_research_by_symbol("AAPL")

        assert len(aapl_research) == 2
        assert all(r["symbol"] == "AAPL" for r in aapl_research)

    def test_search_research(self, temp_db):
        """Test searching research."""
        # Save research
        temp_db.save_research("AAPL", "Analyze Apple earnings", "Report 1")
        temp_db.save_research("MSFT", "Microsoft analysis", "Report 2")

        # Search for "Apple"
        results = temp_db.search_research("Apple")

        assert len(results) >= 1
        assert any("AAPL" in r["symbol"] or "Apple" in r["query"] for r in results)

    def test_get_symbols_list(self, temp_db):
        """Test getting unique symbols."""
        # Save research for different symbols
        temp_db.save_research("AAPL", "Query 1", "Report 1")
        temp_db.save_research("MSFT", "Query 2", "Report 2")
        temp_db.save_research("AAPL", "Query 3", "Report 3")

        symbols = temp_db.get_symbols_list()

        assert len(symbols) == 2
        assert "AAPL" in symbols
        assert "MSFT" in symbols

    def test_delete_research(self, temp_db):
        """Test deleting research."""
        # Save research
        research_id = temp_db.save_research("AAPL", "Query", "Report")

        # Delete it
        deleted = temp_db.delete_research(research_id)
        assert deleted is True

        # Verify it's gone
        research = temp_db.get_research_by_id(research_id)
        assert research is None

    def test_research_count(self, temp_db):
        """Test research counting."""
        assert temp_db.get_research_count() == 0

        temp_db.save_research("AAPL", "Query 1", "Report 1")
        assert temp_db.get_research_count() == 1

        temp_db.save_research("MSFT", "Query 2", "Report 2")
        assert temp_db.get_research_count() == 2
