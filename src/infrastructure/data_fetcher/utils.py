import time
import functools
import threading
import asyncio
from typing import Any, Callable, Dict, Coroutine

class RateLimiter:
    """A thread-safe and async-safe rate limiter using a leaky bucket style logic."""
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.last_call_time: float = 0.0
        self.lock = threading.Lock()
        self.async_lock = asyncio.Lock()
        self.min_interval = 1.0 / calls_per_second

    def wait(self):
        """Synchronous wait."""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
            self.last_call_time = time.time()

    async def async_wait(self):
        """Asynchronous wait."""
        async with self.async_lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                await asyncio.sleep(sleep_time)
            self.last_call_time = time.time()

# Global registry of limiters by domain/label
_limiters: Dict[str, RateLimiter] = {}

def rate_limit(calls_per_second: float = 1.0, label: str = "default"):
    """
    Decorator to limit the rate of function calls (supports sync and async).
    Ensures that calls to functions with the same label are throttled globally.
    """
    if label not in _limiters:
        _limiters[label] = RateLimiter(calls_per_second)
    
    limiter = _limiters[label]

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                await limiter.async_wait()
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                limiter.wait()
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator
