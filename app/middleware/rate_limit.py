import time
import logging
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.exceptions.custom_exceptions import RateLimitException

logger = logging.getLogger(__name__)

# In-memory rate limiting fallback if Redis is not configured or fails
_in_memory_buckets: Dict[str, list] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client
        self.limit = settings.RATE_LIMIT_PER_MINUTE

    async def dispatch(self, request: Request, call_next):
        # Allow documentation through without rate limit
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Identify client (IP address or Authorization subject if decrypted)
        client_ip = request.client.host if request.client else "unknown"
        user_key = f"rate_limit:{client_ip}"

        try:
            if self.redis:
                # Use Redis rate limiter
                current_time = int(time.time())
                pipe = self.redis.pipeline()
                pipe.incr(user_key)
                pipe.expire(user_key, 60)
                results = pipe.execute()
                request_count = results[0]
                if request_count > self.limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "message": "Rate limit exceeded. Please try again in a minute.",
                            "errors": []
                        }
                    )
            else:
                # Use In-Memory fallback rate limiter
                now = time.time()
                # Clean old requests
                if user_key not in _in_memory_buckets:
                    _in_memory_buckets[user_key] = []
                
                # Filter requests in the last 60 seconds
                _in_memory_buckets[user_key] = [t for t in _in_memory_buckets[user_key] if now - t < 60]
                
                if len(_in_memory_buckets[user_key]) >= self.limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "message": "Rate limit exceeded. Please try again in a minute.",
                            "errors": []
                        }
                    )
                
                _in_memory_buckets[user_key].append(now)

        except Exception as e:
            logger.error(f"Rate Limiter error: {e}. Allowing request to pass through.")

        return await call_next(request)
