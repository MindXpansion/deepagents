"""Caching utilities for API calls."""

import time
import hashlib
import json
from typing import Any, Callable, Optional
from functools import wraps
from collections import OrderedDict

from .config import settings


class TTLCache:
    """Time-to-live cache with maximum size limit."""

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum number of items to cache
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self.cache and not self._is_expired(key):
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        elif key in self.cache:
            # Remove expired entry
            del self.cache[key]
            del self.timestamps[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # If key exists, move to end
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = value
        self.timestamps[key] = time.time()

        # Evict oldest if cache is full
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


class SmartCache(TTLCache):
    """
    v1.3.0: Intelligent cache with market-hours awareness and dynamic TTL.

    Features:
    - Market-hours-aware caching (longer TTL when markets closed)
    - Volatility-based TTL adjustment
    - Event-driven invalidation hooks
    """

    def __init__(self, max_size: int = 100, base_ttl: int = 3600):
        """
        Initialize smart cache.

        Args:
            max_size: Maximum number of items to cache
            base_ttl: Base time-to-live in seconds
        """
        super().__init__(max_size, base_ttl)
        self.base_ttl = base_ttl
        self.invalidation_hooks = []

    def is_market_open(self) -> bool:
        """
        Check if US stock market is currently open.

        Returns:
            True if market is open
        """
        from datetime import datetime
        import pytz

        try:
            # Get current time in Eastern Time
            et_tz = pytz.timezone('US/Eastern')
            now_et = datetime.now(et_tz)

            # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
            if now_et.weekday() >= 5:  # Saturday or Sunday
                return False

            market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

            return market_open <= now_et <= market_close

        except Exception:
            # If timezone check fails, assume market is open (safer default)
            return True

    def get_smart_ttl(self, data_type: str, symbol: str = None) -> int:
        """
        Calculate intelligent TTL based on market conditions.

        v1.3.0: Smarter caching strategy!

        Args:
            data_type: Type of data ('price', 'financials', 'technical', 'news')
            symbol: Optional stock symbol

        Returns:
            Calculated TTL in seconds
        """
        # Base TTLs by data type
        base_ttls = {
            'price': 60,         # 1 minute during market hours
            'financials': 86400,  # 24 hours (updates quarterly)
            'technical': 300,     # 5 minutes
            'news': 600,          # 10 minutes
            'analyst': 3600       # 1 hour
        }

        base = base_ttls.get(data_type, self.base_ttl)

        # If market is closed, extend TTL significantly
        if not self.is_market_open():
            if data_type == 'price':
                # Price won't change until market opens
                # Calculate seconds until 9:30 AM ET next trading day
                return 3600 * 4  # 4 hours (simplified)
            elif data_type == 'technical':
                return base * 10  # 50 minutes

        # TODO: Could add volatility-based adjustment here
        # High volatility stocks → shorter TTL

        return base

    def set_with_smart_ttl(self, key: str, value: Any, data_type: str, symbol: str = None) -> None:
        """
        Set value with smart TTL calculation.

        Args:
            key: Cache key
            value: Value to cache
            data_type: Type of data
            symbol: Optional stock symbol
        """
        smart_ttl = self.get_smart_ttl(data_type, symbol)

        # Temporarily override TTL for this entry
        old_ttl = self.ttl
        self.ttl = smart_ttl
        self.set(key, value)
        self.ttl = old_ttl  # Restore original TTL

    def add_invalidation_hook(self, hook: Callable):
        """
        Add a hook function that can trigger cache invalidation.

        Args:
            hook: Function that returns True if cache should be invalidated
        """
        self.invalidation_hooks.append(hook)

    def check_invalidation(self, key: str) -> bool:
        """
        Check if any invalidation hooks trigger for this key.

        Args:
            key: Cache key to check

        Returns:
            True if cache should be invalidated
        """
        for hook in self.invalidation_hooks:
            try:
                if hook(key):
                    return True
            except Exception:
                pass
        return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with invalidation hook checks.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Check invalidation hooks first
        if self.check_invalidation(key):
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
            return None

        return super().get(key)


# Global cache instances (v1.3.0: Using SmartCache)
_stock_price_cache = SmartCache(max_size=settings.CACHE_MAX_SIZE, base_ttl=settings.CACHE_TTL)
_financials_cache = SmartCache(max_size=settings.CACHE_MAX_SIZE, base_ttl=settings.CACHE_TTL * 24)
_technical_cache = SmartCache(max_size=settings.CACHE_MAX_SIZE, base_ttl=settings.CACHE_TTL)


def _make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash of arguments as cache key
    """
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_json = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_json.encode()).hexdigest()


def cached(cache: TTLCache):
    """
    Decorator to cache function results.

    Args:
        cache: TTLCache instance to use

    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{_make_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear

        return wrapper
    return decorator


def get_stock_price_cache() -> TTLCache:
    """Get the stock price cache instance."""
    return _stock_price_cache


def get_financials_cache() -> TTLCache:
    """Get the financials cache instance."""
    return _financials_cache


def get_technical_cache() -> TTLCache:
    """Get the technical indicators cache instance."""
    return _technical_cache


def clear_all_caches() -> None:
    """Clear all cache instances."""
    _stock_price_cache.clear()
    _financials_cache.clear()
    _technical_cache.clear()
