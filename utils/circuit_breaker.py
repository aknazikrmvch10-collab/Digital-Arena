"""
Advanced Circuit Breaker implementation for external API calls.
Prevents cascade failures and provides resilience.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
import functools
from utils.logging import get_logger

logger = get_logger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    expected_exception: type = Exception
    success_threshold: int = 2          # Successes needed to close circuit

class CircuitBreaker:
    """Enterprise-grade Circuit Breaker pattern implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.success_count = 0
        
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to function."""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await self._call_async(func, *args, **kwargs)
            else:
                return await self._call_sync(func, *args, **kwargs)
        return async_wrapper
    
    async def _call_async(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker HALF_OPEN for {func.__name__}")
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is OPEN for {func.__name__}. "
                    f"Recovery timeout: {self.config.recovery_timeout}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker recorded failure for {func.__name__}: {e}")
            raise
    
    async def _call_sync(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker HALF_OPEN for {func.__name__}")
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is OPEN for {func.__name__}"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker recorded failure for {func.__name__}: {e}")
            raise
    
    def _should_attempt_reset(self) -> bool:
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._reset()
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPENED for {self.config.failure_threshold} failures"
            )
    
    def _reset(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def get_state(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }

class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open."""
    pass

# Pre-configured circuit breakers for different services
ICAFE_BREAKER = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception
))

REDIS_BREAKER = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=10.0,
    expected_exception=ConnectionError
))

DATABASE_BREAKER = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=2,
    recovery_timeout=5.0,
    expected_exception=Exception
))
