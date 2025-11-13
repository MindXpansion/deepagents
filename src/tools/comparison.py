"""Multi-stock comparison tool."""

import logging
import json
import asyncio
from typing import List
from langchain_core.tools import tool

from ..utils.validation import validate_stock_symbol, normalize_stock_symbol, extract_symbols_from_query
from .async_tools import fetch_multiple_symbols_parallel

logger = logging.getLogger(__name__)


def _calculate_composite_scores(data: dict) -> dict:
    """
    Calculate composite scores for value, growth, quality, and momentum.

    Args:
        data: Multi-symbol data dictionary

    Returns:
        Dictionary with calculated scores
    """
    scores = {}

    for symbol, symbol_data in data.items():
        if "error" in symbol_data:
            scores[symbol] = {"error": "Data unavailable"}
            continue

        score = {
            "value_score": 0,
            "growth_score": 0,
            "quality_score": 0,
            "momentum_score": 0,
            "overall_score": 0
        }

        # Value score (lower P/E is better)
        price_data = symbol_data.get("stock_price", {})
        pe_ratio = price_data.get("pe_ratio")
        if pe_ratio and pe_ratio != 'N/A':
            try:
                pe = float(pe_ratio)
                if pe > 0 and pe < 50:  # Reasonable range
                    score["value_score"] = max(0, 10 - (pe / 5))  # Lower P/E = higher score
            except:
                pass

        # Growth score
        financials = symbol_data.get("financials", {})
        profit_margin = financials.get("profit_margin")
        if profit_margin:
            try:
                score["growth_score"] = min(10, profit_margin / 2)  # 20%+ margin = 10 points
            except:
                pass

        # Quality score (from financial health)
        roe = financials.get("roe")
        if roe:
            try:
                score["quality_score"] = min(10, roe / 2)  # 20%+ ROE = 10 points
            except:
                pass

        # Momentum score (from technical signals)
        technical = symbol_data.get("technical", {})
        trend = technical.get("trend_signal", "neutral")
        if trend == "strong_bullish":
            score["momentum_score"] = 10
        elif trend == "bullish":
            score["momentum_score"] = 7
        elif trend == "neutral":
            score["momentum_score"] = 5
        elif trend == "bearish":
            score["momentum_score"] = 3
        elif trend == "strong_bearish":
            score["momentum_score"] = 1

        # Calculate overall score (weighted average)
        score["overall_score"] = round(
            (score["value_score"] * 0.25 +
             score["growth_score"] * 0.25 +
             score["quality_score"] * 0.25 +
             score["momentum_score"] * 0.25),
            1
        )

        scores[symbol] = score

    return scores


def _format_comparison_table(data: dict, scores: dict) -> str:
    """
    Format data into comparison table.

    Args:
        data: Multi-symbol data
        scores: Calculated scores

    Returns:
        Formatted table string
    """
    symbols = list(data.keys())

    # Build comparison table
    table = "\n" + "=" * 80 + "\n"
    table += "COMPARATIVE METRICS TABLE\n"
    table += "=" * 80 + "\n\n"

    # Current Price
    table += "CURRENT PRICE:\n"
    for symbol in symbols:
        price = data[symbol].get("stock_price", {}).get("current_price", "N/A")
        table += f"  {symbol}: ${price}\n"
    table += "\n"

    # Valuation Metrics
    table += "VALUATION:\n"
    for symbol in symbols:
        price_data = data[symbol].get("stock_price", {})
        pe = price_data.get("pe_ratio", "N/A")
        table += f"  {symbol}: P/E = {pe}\n"
    table += "\n"

    # Financial Health
    table += "FINANCIAL HEALTH:\n"
    for symbol in symbols:
        fin = data[symbol].get("financials", {})
        margin = fin.get("profit_margin", "N/A")
        roe = fin.get("roe", "N/A")
        de = fin.get("debt_to_equity", "N/A")
        table += f"  {symbol}: Profit Margin = {margin}%, ROE = {roe}%, D/E = {de}\n"
    table += "\n"

    # Technical Signals
    table += "TECHNICAL SIGNALS:\n"
    for symbol in symbols:
        tech = data[symbol].get("technical", {})
        trend = tech.get("trend_signal", "N/A")
        rsi = tech.get("rsi", "N/A")
        table += f"  {symbol}: Trend = {trend}, RSI = {rsi}\n"
    table += "\n"

    # Analyst Sentiment
    table += "ANALYST SENTIMENT:\n"
    for symbol in symbols:
        analyst = data[symbol].get("analysts", {})
        rating = analyst.get("recommendation_key", "N/A")
        target = analyst.get("target_mean_price", "N/A")
        upside = analyst.get("upside_potential", "N/A")
        table += f"  {symbol}: Rating = {rating}, Target = ${target}, Upside = {upside}\n"
    table += "\n"

    # Composite Scores
    table += "COMPOSITE SCORES (0-10):\n"
    table += f"{'Symbol':<10} {'Value':<8} {'Growth':<8} {'Quality':<8} {'Momentum':<8} {'Overall':<8}\n"
    table += "-" * 60 + "\n"
    for symbol in symbols:
        s = scores.get(symbol, {})
        if "error" not in s:
            table += f"{symbol:<10} {s['value_score']:<8.1f} {s['growth_score']:<8.1f} {s['quality_score']:<8.1f} {s['momentum_score']:<8.1f} {s['overall_score']:<8.1f}\n"
    table += "\n"

    # Rankings
    table += "OVERALL RANKING:\n"
    ranked = sorted(
        [(sym, scores[sym].get("overall_score", 0)) for sym in symbols if "error" not in scores.get(sym, {})],
        key=lambda x: x[1],
        reverse=True
    )
    for i, (symbol, score) in enumerate(ranked, 1):
        table += f"  {i}. {symbol} (Score: {score}/10)\n"

    table += "\n" + "=" * 80 + "\n"

    return table


@tool
def compare_stocks(symbols_str: str) -> str:
    """
    Compare multiple stocks side-by-side across all metrics.

    This tool fetches comprehensive data for multiple stocks in parallel
    and generates a detailed comparison analysis including valuation,
    financials, technical signals, analyst sentiment, and composite scores.

    Args:
        symbols_str: Comma-separated list of stock symbols (e.g., "AAPL,MSFT,GOOGL")

    Returns:
        JSON string with comprehensive comparison data and analysis

    Example:
        compare_stocks("AAPL,MSFT,GOOGL")
    """
    logger.info(f"[TOOL] Comparing stocks: {symbols_str}")

    # Parse and validate symbols
    symbols_raw = [s.strip() for s in symbols_str.split(",")]
    symbols = []

    for symbol in symbols_raw:
        symbol = normalize_stock_symbol(symbol)
        is_valid, error_msg = validate_stock_symbol(symbol)

        if not is_valid:
            logger.error(f"[TOOL ERROR] Invalid symbol: {error_msg}")
            return json.dumps({"error": f"Invalid symbol in list: {error_msg}"})

        symbols.append(symbol)

    if len(symbols) < 2:
        return json.dumps({"error": "Please provide at least 2 symbols for comparison"})

    if len(symbols) > 5:
        return json.dumps({"error": "Maximum 5 symbols allowed for comparison"})

    try:
        # Fetch all data in parallel (async)
        logger.info(f"Fetching data for {len(symbols)} symbols in parallel...")
        data = asyncio.run(fetch_multiple_symbols_parallel(symbols))

        # Calculate composite scores
        scores = _calculate_composite_scores(data)

        # Format comparison table
        comparison_table = _format_comparison_table(data, scores)

        # Build result
        result = {
            "symbols": symbols,
            "comparison_table": comparison_table,
            "detailed_data": data,
            "scores": scores,
            "ranking": sorted(
                [(sym, scores[sym].get("overall_score", 0)) for sym in symbols if "error" not in scores.get(sym, {})],
                key=lambda x: x[1],
                reverse=True
            )
        }

        logger.info(f"[TOOL RESULT] Successfully compared {len(symbols)} stocks")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL ERROR] Comparison failed")
        return json.dumps({"error": f"Failed to compare stocks: {str(e)}"})
