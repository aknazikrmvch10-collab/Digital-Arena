"""
Enterprise-grade multi-level caching system with intelligent invalidation.
Supports Redis, memory, and cache warming strategies.
"""

import asyncio
import json
import hashlib
import time
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import functools
from datetime import datetime, timedelta

from services.redis_client import cache
from utils.logging import get_logger

logger = get_logger(__name__)

class CacheLevel(Enum):
    L1_MEMORY = "l1_memory"  # Fastest, process-local
    L2_REDIS = "l2_redis"    # Fast, distributed
    L3_DATABASE = "l3_database"  # Slowest, persistent

@dataclass
class CacheConfig:
    ttl: int = 300                    # Time to live in seconds
    max_size: int = 1000              # Max items for L1 cache
    enable_warmup: bool = True        # Pre-warm cache on startup
    invalidation_strategy: str = "ttl"  # ttl, event, hybrid
    compression: bool = True          # Compress large objects

@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    ttl: int
    hits: int = 0
    level: CacheLevel = CacheLevel.L1_MEMORY
    
    @property
    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)
    
    @property
    def age(self) -> float:
        return time.time() - self.timestamp

class AdvancedCache:
    """Enterprise multi-level caching with intelligent invalidation."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._l1_cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._stats = {
            "l1_hits": 0, "l1_misses": 0,
            "l2_hits": 0, "l2_misses": 0,
            "evictions": 0, "invalidations": 0
        }
        
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from function arguments."""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.compression and len(str(value)) > 1024:
            import gzip
            return gzip.compress(json.dumps(value).encode())
        return json.dumps(value).encode()
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            if self.config.compression and data.startswith(b'\x1f\x8b'):
                import gzip
                return json.loads(gzip.decompress(data).decode())
            return json.loads(data.decode())
        except Exception as e:
            logger.error(f"Cache deserialization error: {e}")
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, checking L1 then L2."""
        # Check L1 (memory) cache first
        if key in self._l1_cache:
            entry = self._l1_cache[key]
            if not entry.is_expired:
                entry.hits += 1
                self._update_access_order(key)
                self._stats["l1_hits"] += 1
                logger.debug(f"L1 cache hit: {key}")
                return entry.value
            else:
                del self._l1_cache[key]
                self._access_order.remove(key)
        
        # Check L2 (Redis) cache
        try:
            data = await cache.get(key)
            if data:
                value = self._deserialize(data)
                if value is not None:
                    # Promote to L1
                    await self._set_l1(key, value)
                    self._stats["l2_hits"] += 1
                    logger.debug(f"L2 cache hit: {key}")
                    return value
        except Exception as e:
            logger.error(f"L2 cache error: {e}")
        
        self._stats["l1_misses"] += 1
        self._stats["l2_misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL override."""
        ttl = ttl or self.config.ttl
        
        # Set in L1 (memory)
        await self._set_l1(key, value, ttl)
        
        # Set in L2 (Redis)
        try:
            serialized = self._serialize(value)
            await cache.set(key, serialized, ttl)
        except Exception as e:
            logger.error(f"L2 cache set error: {e}")
    
    async def _set_l1(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in L1 cache with LRU eviction."""
        ttl = ttl or self.config.ttl
        
        # Evict if necessary
        if len(self._l1_cache) >= self.config.max_size:
            await self._evict_lru()
        
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            level=CacheLevel.L1_MEMORY
        )
        
        self._l1_cache[key] = entry
        self._update_access_order(key)
    
    def _update_access_order(self, key: str) -> None:
        """Update LRU access order."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def _evict_lru(self) -> None:
        """Evict least recently used item from L1 cache."""
        if not self._access_order:
            return
        
        lru_key = self._access_order.pop(0)
        if lru_key in self._l1_cache:
            del self._l1_cache[lru_key]
            self._stats["evictions"] += 1
            logger.debug(f"LRU evicted: {lru_key}")
    
    async def invalidate(self, pattern: Optional[str] = None) -> None:
        """Invalidate cache entries by pattern or all."""
        if pattern:
            # Pattern-based invalidation
            keys_to_remove = [k for k in self._l1_cache.keys() if pattern in k]
            for key in keys_to_remove:
                if key in self._l1_cache:
                    del self._l1_cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            # Also invalidate in Redis
            try:
                await cache.delete_pattern(pattern)
            except Exception as e:
                logger.error(f"Redis invalidation error: {e}")
        else:
            # Clear all
            self._l1_cache.clear()
            self._access_order.clear()
            
            try:
                await cache.clear()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        
        self._stats["invalidations"] += 1
        logger.info(f"Cache invalidated: pattern={pattern}")
    
    async def warmup(self, data_loader: Dict[str, Callable]) -> None:
        """Warm up cache with pre-defined data."""
        if not self.config.enable_warmup:
            return
        
        logger.info("Starting cache warmup...")
        for key_prefix, loader in data_loader.items():
            try:
                data = await loader()
                if data:
                    await self.set(f"warmup:{key_prefix}", data)
                    logger.info(f"Warmed up cache: {key_prefix}")
            except Exception as e:
                logger.error(f"Cache warmup error for {key_prefix}: {e}")
        
        logger.info("Cache warmup completed")
    
    def cache(self, prefix: str, ttl: Optional[int] = None):
        """Decorator for caching function results."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached = await self.get(key)
                if cached is not None:
                    return cached
                
                # Execute function and cache result
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                await self.set(key, result, ttl)
                return result
            
            return async_wrapper
        return decorator
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self._stats["l1_hits"] + self._stats["l1_misses"]
        l1_hit_rate = (self._stats["l1_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._stats,
            "l1_hit_rate": round(l1_hit_rate, 2),
            "l1_size": len(self._l1_cache),
            "l1_max_size": self.config.max_size
        }

# Global cache instance
cache_config = CacheConfig(
    ttl=300,
    max_size=1000,
    enable_warmup=True,
    compression=True
)

advanced_cache = AdvancedCache(cache_config)
