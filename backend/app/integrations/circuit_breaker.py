import time
import asyncio
import inspect
import functools
import structlog
from typing import Callable, Any, Optional

logger = structlog.get_logger()

class CircuitBreakerOpenException(Exception):
    """
    Raised when a call is attempted while the circuit breaker is in the OPEN state.
    """
    pass

class CircuitBreaker:
    """
    A Circuit Breaker implementation that supports both synchronous and asynchronous functions.
    It tracks failures and opens the circuit if the failures exceed a threshold.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_state_change = time.time()

    def _check_state(self, func_name: str):
        if self.state == "OPEN":
            elapsed = time.time() - self.last_state_change
            if elapsed > self.recovery_timeout:
                self.state = "HALF-OPEN"
                self.last_state_change = time.time()
                logger.info("Circuit transition to HALF-OPEN", function=func_name)
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit open for {func_name}. Remaining recovery time: {self.recovery_timeout - elapsed:.2f}s"
                )

    def _handle_success(self, func_name: str):
        if self.state == "HALF-OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            self.last_state_change = time.time()
            logger.info("Circuit closed successfully", function=func_name)
        elif self.state == "CLOSED" and self.failure_count > 0:
            # Gradually reset failures on successes
            self.failure_count = 0

    def _handle_failure(self, func_name: str, exception: Exception):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error(
                "Circuit opened due to failures",
                function=func_name,
                failures=self.failure_count,
                error=str(exception)
            )

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                self._check_state(func.__name__)
                try:
                    result = await func(*args, **kwargs)
                    self._handle_success(func.__name__)
                    return result
                except Exception as e:
                    self._handle_failure(func.__name__, e)
                    raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                self._check_state(func.__name__)
                try:
                    result = func(*args, **kwargs)
                    self._handle_success(func.__name__)
                    return result
                except Exception as e:
                    self._handle_failure(func.__name__, e)
                    raise e
            return sync_wrapper
