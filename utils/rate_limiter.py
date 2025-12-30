"""
Rate limiting utilities for API calls.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import deque
import threading


class RateLimiter:
    """
    Token bucket rate limiter.
    Ensures we don't exceed API rate limits.
    """

    def __init__(self, max_requests: int, time_window_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed
            time_window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.requests: deque = deque()
        self.lock = threading.Lock()

    def acquire(self, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.

        Args:
            block: If True, wait until rate limit allows
            timeout: Maximum time to wait (None = forever)

        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()

        while True:
            with self.lock:
                now = datetime.now()
                cutoff = now - timedelta(seconds=self.time_window)

                # Remove old requests outside the time window
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

                # Check if we can make a request
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True

            if not block:
                return False

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # Wait a bit before trying again
            time.sleep(0.1)

    def wait(self):
        """Wait until rate limit allows a request."""
        self.acquire(block=True)

    def get_wait_time(self) -> float:
        """Get estimated wait time until next request is allowed."""
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.time_window)

            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                return 0.0

            # Calculate wait time
            oldest = self.requests[0]
            wait_until = oldest + timedelta(seconds=self.time_window)
            wait_seconds = (wait_until - now).total_seconds()

            return max(0.0, wait_seconds)

    def reset(self):
        """Reset the rate limiter."""
        with self.lock:
            self.requests.clear()


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different APIs.
    """

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}

    def add_limiter(self, name: str, max_requests: int, time_window_seconds: int):
        """Add a rate limiter for a specific API."""
        self.limiters[name] = RateLimiter(max_requests, time_window_seconds)

    def acquire(self, name: str, block: bool = True) -> bool:
        """Acquire permission for a specific API."""
        if name not in self.limiters:
            return True  # No limiter = always allow

        return self.limiters[name].acquire(block=block)

    def wait(self, name: str):
        """Wait for a specific API's rate limit."""
        if name in self.limiters:
            self.limiters[name].wait()

    def get_status(self) -> Dict:
        """Get status of all rate limiters."""
        status = {}
        for name, limiter in self.limiters.items():
            with limiter.lock:
                status[name] = {
                    'max_requests': limiter.max_requests,
                    'time_window': limiter.time_window,
                    'current_requests': len(limiter.requests),
                    'wait_time': limiter.get_wait_time(),
                }
        return status


# Pre-configured rate limiters for common APIs
sec_limiter = RateLimiter(max_requests=10, time_window_seconds=1)  # SEC: 10 req/sec
twitter_limiter = RateLimiter(max_requests=50, time_window_seconds=900)  # Twitter: ~50/15min for tweets

# Global multi-limiter
api_limiters = MultiRateLimiter()
api_limiters.add_limiter('sec', max_requests=10, time_window_seconds=1)
api_limiters.add_limiter('twitter', max_requests=50, time_window_seconds=900)
api_limiters.add_limiter('discord', max_requests=30, time_window_seconds=60)


def rate_limited(limiter_name: str):
    """Decorator to apply rate limiting to a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            api_limiters.wait(limiter_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test rate limiter
    print("Testing rate limiter...")

    limiter = RateLimiter(max_requests=3, time_window_seconds=2)

    for i in range(5):
        start = time.time()
        acquired = limiter.acquire(block=True, timeout=5)
        elapsed = time.time() - start
        print(f"Request {i+1}: acquired={acquired}, waited={elapsed:.2f}s")

    print("\nMulti-limiter status:")
    status = api_limiters.get_status()
    for name, info in status.items():
        print(f"  {name}: {info}")
