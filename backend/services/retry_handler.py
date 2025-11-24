"""
Retry Handler Service

Provides retry logic with exponential backoff and circuit breaker pattern
for resilient API calls and operations.
"""

import logging
import time
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
from collections import defaultdict

logger = logging.getLogger("owlin.services.retry_handler")


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting reset
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        # half_open state - allow one attempt
        return True
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None


class RetryHandler:
    """Handles retries with exponential backoff."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize retry handler with circuit breakers.
        
        Args:
            failure_threshold: Default failure threshold for circuit breakers
            timeout: Default timeout for circuit breakers
        """
        self.default_failure_threshold = failure_threshold
        self.default_timeout = timeout
        self.circuit_breakers: dict[str, CircuitBreaker] = defaultdict(
            lambda: CircuitBreaker(failure_threshold, timeout)
        )
    
    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on: Tuple[Type[Exception], ...] = (Exception,),
        circuit_breaker_key: Optional[str] = None
    ) -> Any:
        """
        Execute function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            retry_on: Tuple of exception types to retry on
            circuit_breaker_key: Key for circuit breaker (None = no circuit breaker)
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        circuit_breaker = None
        if circuit_breaker_key:
            circuit_breaker = self.circuit_breakers[circuit_breaker_key]
            if not circuit_breaker.can_attempt():
                raise Exception(f"Circuit breaker is open for {circuit_breaker_key}")
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func()
                
                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except retry_on as e:
                last_exception = e
                
                # Record failure
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                if attempt < max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
        
        # All retries exhausted
        raise last_exception


# Global retry handler instance
_retry_handler = RetryHandler()


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on: tuple[Type[Exception], ...] = (Exception,),
    circuit_breaker_key: Optional[str] = None
):
    """
    Decorator for retry with exponential backoff.
    
    Usage:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            def call_func():
                return func(*args, **kwargs)
            
            return _retry_handler.retry_with_backoff(
                call_func,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retry_on=retry_on,
                circuit_breaker_key=circuit_breaker_key
            )
        return wrapper
    return decorator

