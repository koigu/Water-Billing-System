"""
Caching utilities for analytics service.
Provides in-memory caching with TTL support.
"""
import time
import hashlib
import json
from datetime import datetime
from typing import Any, Optional, Callable, Dict, List
from functools import wraps
import threading
import logging

logger = logging.getLogger("cache")


class CacheEntry:
    """Represents a cached item with TTL."""
    
    def __init__(self, value: Any, ttl_seconds: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def get(self) -> Any:
        """Get the value and increment access count."""
        self.access_count += 1
        return self.value
    
    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        remaining = self.ttl_seconds - (time.time() - self.created_at)
        return max(0, remaining)


class AnalyticsCache:
    """Thread-safe in-memory cache for analytics data."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        # Convert args and kwargs to a hashable string
        key_parts = [prefix]
        
        for arg in args:
            key_parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        key_string = "::".join(key_parts)
        
        # Hash if too long
        if len(key_string) > 256:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}::{key_hash}"
        
        return key_string
    
    def get(self, key: str) -> tuple:
        """
        Get a value from cache.
        
        Returns:
            Tuple of (value, is_hit) where is_hit indicates if cache had the key
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None, False
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None, False
            
            return entry.get(), True
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if not specified)
        """
        with self._lock:
            # Evict oldest entries if cache is full
            while len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            self._cache[key] = CacheEntry(value, ttl)
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry from cache."""
        if not self._cache:
            return
        
        # Find oldest entry
        oldest_key = None
        oldest_time = float('inf')
        
        for key, entry in self._cache.items():
            if entry.created_at < oldest_time:
                oldest_time = entry.created_at
                oldest_key = key
        
        if oldest_key:
            del self._cache[oldest_key]
            self._stats["evictions"] += 1
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache key.
        
        Returns:
            True if key was found and invalidated, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * as wildcard)
        """
        import fnmatch
        count = 0
        
        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        
        return count
    
    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidate all keys with a given prefix.
        
        Args:
            prefix: Key prefix to invalidate
        """
        return self.invalidate_pattern(f"{prefix}*")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"],
                "total_entries": len(self._cache),
                "hit_rate_percent": round(hit_rate, 2),
                "max_size": self._max_size,
                "default_ttl_seconds": self._default_ttl
            }
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache."""
        count = 0
        
        with self._lock:
            keys_to_delete = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
                self._stats["expirations"] += 1
        
        return count
    
    def get_ttl_info(self, key: str) -> Optional[dict]:
        """Get TTL information for a specific key."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            remaining = entry.remaining_ttl()
            
            return {
                "key": key,
                "remaining_ttl_seconds": remaining,
                "original_ttl_seconds": entry.ttl_seconds,
                "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                "expires_at": datetime.fromtimestamp(
                    entry.created_at + entry.ttl_seconds
                ).isoformat(),
                "access_count": entry.access_count,
                "is_expired": remaining == 0
            }


# Global cache instance
_analytics_cache: Optional[AnalyticsCache] = None


def get_cache() -> AnalyticsCache:
    """Get or create the global analytics cache instance."""
    global _analytics_cache
    if _analytics_cache is None:
        _analytics_cache = AnalyticsCache(
            max_size=1000,
            default_ttl=300  # 5 minutes default TTL
        )
    return _analytics_cache


def clear_analytics_cache() -> None:
    """Clear the global analytics cache."""
    cache = get_cache()
    cache.clear()
    logger.info("Analytics cache cleared")


def cache_decorator(
    prefix: str,
    ttl_seconds: int = 300,
    skip_on_error: bool = True,
    include_args_in_key: bool = True
):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        ttl_seconds: TTL in seconds
        skip_on_error: If True, don't cache if function raises exception
        include_args_in_key: If True, include function args in cache key
    
    Example:
        @cache_decorator(prefix="usage", ttl_seconds=600)
        def get_customer_usage(customer_id: int, months: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if include_args_in_key:
                cache_key = get_cache()._generate_key(prefix, *args, **kwargs)
            else:
                cache_key = get_cache()._generate_key(prefix)
            
            # Try to get from cache
            cache = get_cache()
            cached_value, is_hit = cache.get(cache_key)
            
            if is_hit:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            logger.debug(f"Cache miss for {cache_key}")
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                
                # Cache the result
                cache.set(cache_key, result, ttl_seconds)
                
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                if not skip_on_error:
                    raise
                return None
        
        return wrapper
    return decorator


def cached_method(
    prefix: str,
    ttl_seconds: int = 300,
    include_args_in_key: bool = True
):
    """
    Decorator for caching instance method results.
    Uses instance identity and method arguments for cache key.
    
    Args:
        prefix: Cache key prefix
        ttl_seconds: TTL in seconds
        include_args_in_key: If True, include method args in cache key
    
    Example:
        class MyService:
            @cached_method(prefix="data", ttl_seconds=600)
            def get_data(self, param1: int) -> dict:
                ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Include instance id to separate caches per instance
            instance_id = id(self)
            
            if include_args_in_key:
                cache_key = get_cache()._generate_key(
                    f"{prefix}:{instance_id}",
                    *args,
                    **kwargs
                )
            else:
                cache_key = get_cache()._generate_key(f"{prefix}:{instance_id}")
            
            # Try to get from cache
            cache = get_cache()
            cached_value, is_hit = cache.get(cache_key)
            
            if is_hit:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            logger.debug(f"Cache miss for {cache_key}")
            
            # Execute method
            result = func(self, *args, **kwargs)
            
            # Cache the result
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_on_change(collection_name: str) -> Callable:
    """
    Decorator that invalidates cache when data changes in a collection.
    
    Args:
        collection_name: Name of the collection to invalidate on change
    
    Example:
        @invalidate_cache_on_change("usage_trends")
        def update_usage_trend(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache for this collection
            cache = get_cache()
            cache.invalidate_prefix(f"*{collection_name}*")
            
            logger.info(f"Cache invalidated for collection: {collection_name}")
            
            return result
        
        return wrapper
    return decorator


class CacheWarmup:
    """Pre-populate cache with frequently accessed data."""
    
    def __init__(self, cache: Optional[AnalyticsCache] = None):
        self.cache = cache or get_cache()
        self._warmup_tasks: List[dict] = []
    
    def add_warmup_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        ttl_seconds: int = 600
    ):
        """
        Add a task to the warmup queue.
        
        Args:
            name: Name of the task
            func: Function to call
            args: Positional arguments
            kwargs: Keyword arguments
            ttl_seconds: TTL for cached result
        """
        self._warmup_tasks.append({
            "name": name,
            "func": func,
            "args": args,
            "kwargs": kwargs or {},
            "ttl_seconds": ttl_seconds
        })
    
    def run(self, parallel: bool = False) -> dict:
        """
        Execute all warmup tasks.
        
        Args:
            parallel: If True, run tasks in parallel threads
        
        Returns:
            Dictionary with warmup results
        """
        results = {
            "success": 0,
            "failed": 0,
            "tasks": []
        }
        
        for task in self._warmup_tasks:
            try:
                if parallel:
                    # Run in separate thread
                    thread = threading.Thread(
                        target=self._execute_task,
                        args=(task,)
                    )
                    thread.start()
                    results["success"] += 1
                else:
                    self._execute_task(task)
                    results["success"] += 1
                
                results["tasks"].append({
                    "name": task["name"],
                    "status": "success"
                })
            
            except Exception as e:
                logger.error(f"Warmup task {task['name']} failed: {e}")
                results["failed"] += 1
                results["tasks"].append({
                    "name": task["name"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _execute_task(self, task: dict):
        """Execute a single warmup task."""
        cache_key = get_cache()._generate_key(
            f"warmup:{task['name']}",
            *task.get("args", ()),
            **task.get("kwargs", {})
        )
        
        # Check if already cached
        cached_value, is_hit = self.cache.get(cache_key)
        if is_hit:
            return
        
        # Execute and cache
        result = task["func"](*task["args"], **task["kwargs"])
        self.cache.set(cache_key, result, task["ttl_seconds"])
        
        logger.debug(f"Warmup task {task['name']} completed")


def get_cache_stats() -> dict:
    """Get global cache statistics."""
    return get_cache().get_stats()

