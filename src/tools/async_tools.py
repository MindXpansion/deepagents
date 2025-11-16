"""Async versions of financial tools for parallel execution."""

import asyncio
import logging
from typing import Dict, List
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

from .stock_data import _fetch_stock_price
from .financials import _fetch_financial_statements
from .technical_indicators import _fetch_technical_indicators
from .news_sentiment import _fetch_news_sentiment
from .analyst_data import _fetch_analyst_recommendations

logger = logging.getLogger(__name__)

# Thread pool for running sync yfinance calls in async context
_executor = ThreadPoolExecutor(max_workers=10)


async def fetch_stock_price_async(symbol: str) -> dict:
    """
    Async wrapper for stock price fetching.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with stock price data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_stock_price, symbol)


async def fetch_financial_statements_async(symbol: str) -> dict:
    """
    Async wrapper for financial statements fetching.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with financial statement data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_financial_statements, symbol)


async def fetch_technical_indicators_async(symbol: str, period: str = "3mo") -> dict:
    """
    Async wrapper for technical indicators calculation.

    Args:
        symbol: Stock ticker symbol
        period: Historical data period

    Returns:
        Dictionary with technical indicator data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_technical_indicators, symbol, period)


async def fetch_news_sentiment_async(symbol: str, max_articles: int = 5) -> dict:
    """
    Async wrapper for news sentiment analysis.

    Args:
        symbol: Stock ticker symbol
        max_articles: Maximum number of articles

    Returns:
        Dictionary with news sentiment data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_news_sentiment, symbol, max_articles)


async def fetch_analyst_recommendations_async(symbol: str) -> dict:
    """
    Async wrapper for analyst recommendations fetching.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with analyst recommendation data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_analyst_recommendations, symbol)


async def fetch_all_data_parallel(symbol: str) -> Dict[str, dict]:
    """
    Fetch all financial data for a symbol in parallel.

    This dramatically speeds up data gathering by running all
    API calls concurrently instead of sequentially.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with all fetched data
    """
    logger.info(f"Fetching all data for {symbol} in parallel...")

    # Launch all requests concurrently
    results = await asyncio.gather(
        fetch_stock_price_async(symbol),
        fetch_financial_statements_async(symbol),
        fetch_technical_indicators_async(symbol),
        fetch_news_sentiment_async(symbol),
        fetch_analyst_recommendations_async(symbol),
        return_exceptions=True  # Don't fail if one request fails
    )

    # Package results
    data = {
        "stock_price": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "financials": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "technical": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "news": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
        "analysts": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
    }

    logger.info(f"Parallel fetch complete for {symbol}")
    return data


async def fetch_multiple_symbols_parallel(symbols: List[str]) -> Dict[str, Dict[str, dict]]:
    """
    Fetch data for multiple symbols in parallel.

    Useful for comparison analysis.

    Args:
        symbols: List of stock ticker symbols

    Returns:
        Dictionary mapping symbols to their data
    """
    logger.info(f"Fetching data for {len(symbols)} symbols in parallel...")

    # Fetch all symbols concurrently
    tasks = [fetch_all_data_parallel(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Package results
    data = {}
    for symbol, result in zip(symbols, results):
        if isinstance(result, Exception):
            data[symbol] = {"error": str(result)}
        else:
            data[symbol] = result

    logger.info(f"Parallel fetch complete for all symbols")
    return data
