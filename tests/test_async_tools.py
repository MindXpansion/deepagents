"""Unit tests for async tools."""

import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Note: These tests would require mocking yfinance calls in production
# For now, we'll test the structure and basic functionality


class TestAsyncTools:
    """Test async tool wrappers."""

    def test_async_tools_import(self):
        """Test that async tools can be imported."""
        from src.tools.async_tools import (
            fetch_stock_price_async,
            fetch_financial_statements_async,
            fetch_technical_indicators_async,
            fetch_news_sentiment_async,
            fetch_analyst_recommendations_async,
            fetch_all_data_parallel,
            fetch_multiple_symbols_parallel
        )

        # Check all functions exist
        assert callable(fetch_stock_price_async)
        assert callable(fetch_financial_statements_async)
        assert callable(fetch_technical_indicators_async)
        assert callable(fetch_news_sentiment_async)
        assert callable(fetch_analyst_recommendations_async)
        assert callable(fetch_all_data_parallel)
        assert callable(fetch_multiple_symbols_parallel)

    @pytest.mark.asyncio
    async def test_fetch_all_data_parallel_structure(self):
        """Test that fetch_all_data_parallel returns correct structure."""
        # This would need mocking in real tests
        # For now just test it's callable and returns a coroutine
        from src.tools.async_tools import fetch_all_data_parallel

        assert asyncio.iscoroutinefunction(fetch_all_data_parallel)


class TestComparisonTool:
    """Test comparison tool."""

    def test_comparison_tool_import(self):
        """Test that comparison tool can be imported."""
        from src.tools.comparison import compare_stocks

        assert callable(compare_stocks)
        assert hasattr(compare_stocks, 'name')  # LangChain tool decorator adds name

    def test_score_calculation(self):
        """Test composite score calculation."""
        from src.tools.comparison import _calculate_composite_scores

        # Test with sample data
        sample_data = {
            "AAPL": {
                "stock_price": {"pe_ratio": 25},
                "financials": {"profit_margin": 25, "roe": 30},
                "technical": {"trend_signal": "bullish"}
            }
        }

        scores = _calculate_composite_scores(sample_data)

        assert "AAPL" in scores
        assert "overall_score" in scores["AAPL"]
        assert 0 <= scores["AAPL"]["overall_score"] <= 10
