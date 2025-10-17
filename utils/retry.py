import asyncio
import functools
from typing import Callable, TypeVar, Optional, Tuple, Type, Awaitable, Coroutine, Any
from utils.logger import setup_logger
from utils.exceptions import BrowserAutomationError

logger = setup_logger(__name__)

T = TypeVar('T')

class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions

async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from successful function call
        
    Raises:
        Exception from last failed attempt
    """
    if config is None:
        config = RetryConfig()
    
    last_exception: Optional[Exception] = None
    delay = config.initial_delay
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Success after {attempt} attempts")
            return result
            
        except config.exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(
                    f"Failed after {config.max_attempts} attempts: {e}"
                )
                raise
            
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            await asyncio.sleep(delay)
            delay = min(delay * config.exponential_base, config.max_delay)
    
    # This should never be reached due to raise in the loop, but for type safety
    if last_exception is not None:
        raise last_exception
    raise Exception("Retry failed with no exception recorded")

def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        
    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                logger.info("Circuit breaker: Attempting reset")
            else:
                raise BrowserAutomationError(
                    f"Circuit breaker is OPEN. "
                    f"Wait {self.recovery_timeout}s before retry."
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        import time
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful execution."""
        if self.state == "half-open":
            logger.info("Circuit breaker: Reset to CLOSED")
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self) -> None:
        """Handle failed execution."""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(
                f"Circuit breaker: OPENED after {self.failure_count} failures"
            )