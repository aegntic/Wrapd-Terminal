#!/usr/bin/env python3
# WRAPD: Retry Logic for API Calls

import asyncio
import time
import logging
import random
from typing import Callable, Any, Optional, List, Type
from .error_handling import APIConnectionError, RateLimitError

class RetryHandler:
    """Advanced retry handler with backoff strategies"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 backoff_factor: float = 2.0,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 jitter: bool = True,
                 retryable_errors: Optional[List[Type[Exception]]] = None):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to delays
            retryable_errors: List of exception types that should trigger retries
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        
        # Default retryable errors
        if retryable_errors is None:
            self.retryable_errors = [
                APIConnectionError,
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
            ]
        else:
            self.retryable_errors = retryable_errors
        
        self.logger = logging.getLogger("wrapd.retry_handler")
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt}/{self.max_retries}")
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # Check if error is retryable
                if not self._is_retryable_error(e):
                    self.logger.debug(f"Non-retryable error: {type(e).__name__}")
                    raise e
                
                # Don't delay after the last attempt
                if attempt == self.max_retries:
                    break
                
                # Handle rate limiting specially
                if isinstance(e, RateLimitError):
                    delay = self._get_rate_limit_delay(e)
                else:
                    delay = self._calculate_delay(attempt)
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        self.logger.error(f"All {self.max_retries} retries exhausted")
        raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error should trigger a retry"""
        return any(isinstance(error, error_type) for error_type in self.retryable_errors)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff"""
        # Exponential backoff: base_delay * (backoff_factor ^ attempt)
        delay = self.base_delay * (self.backoff_factor ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def _get_rate_limit_delay(self, error: RateLimitError) -> float:
        """Get delay for rate limit errors"""
        if hasattr(error, 'retry_after') and error.retry_after:
            # Use server-provided retry delay
            delay = float(error.retry_after)
        else:
            # Use default rate limit delay
            delay = 60.0  # 1 minute default
        
        # Add small random jitter
        if self.jitter:
            jitter = random.uniform(0, 5)  # 0-5 seconds
            delay += jitter
        
        return min(delay, self.max_delay)

class CircuitBreaker:
    """Circuit breaker pattern for failing services"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying again
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = logging.getLogger("wrapd.circuit_breaker")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError if circuit is open
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                self._reset()
                self.logger.info("Circuit breaker reset to CLOSED state")
            
            return result
            
        except self.expected_exception as e:
            self._record_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _record_failure(self):
        """Record a failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )
    
    def _reset(self):
        """Reset circuit breaker to closed state"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class AdaptiveRetryHandler(RetryHandler):
    """Retry handler that adapts based on historical success rates"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Track success/failure rates
        self.success_count = 0
        self.failure_count = 0
        self.recent_response_times = []
        self.max_response_time_samples = 50
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Enhanced retry with adaptive behavior"""
        start_time = time.time()
        
        try:
            result = await super().retry_with_backoff(func, *args, **kwargs)
            
            # Record success
            self.success_count += 1
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            
            return result
            
        except Exception as e:
            # Record failure
            self.failure_count += 1
            raise e
    
    def _record_response_time(self, response_time: float):
        """Record response time for adaptive behavior"""
        self.recent_response_times.append(response_time)
        
        # Keep only recent samples
        if len(self.recent_response_times) > self.max_response_time_samples:
            self.recent_response_times.pop(0)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate adaptive delay based on historical performance"""
        base_delay = super()._calculate_delay(attempt)
        
        # Adjust based on success rate
        total_attempts = self.success_count + self.failure_count
        if total_attempts > 10:  # Only adapt after enough data
            success_rate = self.success_count / total_attempts
            
            if success_rate < 0.5:  # Low success rate
                base_delay *= 2.0  # Increase delays
            elif success_rate > 0.9:  # High success rate
                base_delay *= 0.7  # Decrease delays
        
        # Adjust based on response times
        if self.recent_response_times:
            avg_response_time = sum(self.recent_response_times) / len(self.recent_response_times)
            
            if avg_response_time > 10.0:  # Slow responses
                base_delay *= 1.5
            elif avg_response_time < 2.0:  # Fast responses
                base_delay *= 0.8
        
        return max(self.base_delay, base_delay)
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        total_attempts = self.success_count + self.failure_count
        success_rate = self.success_count / total_attempts if total_attempts > 0 else 0
        
        avg_response_time = 0
        if self.recent_response_times:
            avg_response_time = sum(self.recent_response_times) / len(self.recent_response_times)
        
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "total_attempts": total_attempts
        }

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, requests_per_second: float = 1.0, burst_size: int = 5):
        """
        Initialize rate limiter
        
        Args:
            requests_per_second: Allowed requests per second
            burst_size: Maximum burst size
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        
        self.tokens = burst_size
        self.last_update = time.time()
        
        self.logger = logging.getLogger("wrapd.rate_limiter")
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        now = time.time()
        
        # Add tokens based on time passed
        time_passed = now - self.last_update
        self.tokens += time_passed * self.requests_per_second
        self.tokens = min(self.tokens, self.burst_size)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.requests_per_second
            self.logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
            # Try again after waiting
            self.tokens = 0  # All tokens used after waiting
            return True
    
    async def wait_for_tokens(self, tokens: int = 1):
        """Wait until tokens are available"""
        await self.acquire(tokens)