#algorithm from:
#https://oneuptime.com/blog/post/2026-01-21-sliding-window-rate-limiting-python/view

from dataclasses import dataclass
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import time
import logging
import logging.handlers

# Log rate limit events to a rotating file (max 5MB, keep 3 backups)
_handler = logging.handlers.RotatingFileHandler(
    "rate_limit.log", maxBytes=5 * 1024 * 1024, backupCount=3
)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

logger = logging.getLogger("rate_limit")
logger.setLevel(logging.WARNING)
logger.addHandler(_handler)


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: float
    reset_after: float


class SlidingWindow:
    """
    In-memory sliding window rate limiter.
    Stores request timestamps per key. No external dependencies required.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._log: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> RateLimitResult:
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = self._log[key]

        # Drop entries outside the window
        self._log[key] = [t for t in timestamps if t > cutoff]
        count = len(self._log[key])

        if count >= self.max_requests:
            oldest = self._log[key][0]
            retry_after = max(0.0, oldest + self.window_seconds - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
                reset_after=retry_after,
            )

        self._log[key].append(now)
        return RateLimitResult(
            allowed=True,
            remaining=self.max_requests - count - 1,
            retry_after=0.0,
            reset_after=self.window_seconds,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that applies rate limiting to all requests.

    Adds rate limit headers to responses:
    - X-RateLimit-Limit: Max requests allowed
    - X-RateLimit-Remaining: Requests remaining
    - X-RateLimit-Reset: Seconds until window resets
    """

    def __init__(
        self,
        app,
        limiter: SlidingWindow,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func or self._default_key

    def _default_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        # ESP32 can send many events (e.g. power samples every 100ms); do not throttle ingest.
        if request.url.path in ("/health", "/ready", "/api/events/ingest"):
            return await call_next(request)

        key = self.key_func(request)
        result = self.limiter.check(key)

        if not result.allowed:
            logger.warning(
                "Rate limit exceeded | ip=%s method=%s path=%s retry_after=%.1fs",
                key, request.method, request.url.path, result.retry_after
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": result.retry_after
                },
                headers={
                    "X-RateLimit-Limit": str(self.limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_after)),
                    "Retry-After": str(int(result.retry_after))
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_after))
        return response
