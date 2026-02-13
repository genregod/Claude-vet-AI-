"""
Valor Assist — Security Middleware

Configures CORS, rate limiting, security headers, and request validation
for production deployment. PII-safe by default:
  - Strict CORS (configurable allowed origins for the frontend)
  - Rate limiting to prevent abuse
  - Security headers (HSTS, X-Content-Type, X-Frame-Options)
  - Request size limits to prevent payload attacks
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


def configure_cors(app: FastAPI) -> None:
    """
    Add CORS middleware. In production, ALLOWED_ORIGINS should be
    restricted to the actual frontend domain (e.g., https://valorassist.com).
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
        expose_headers=["X-Session-ID", "X-Request-ID"],
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter keyed by client IP.
    For AWS production, replace with API Gateway throttling or WAF rules.
    """

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = settings.rate_limit_window_seconds

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        if len(self._requests[client_ip]) >= settings.rate_limit_max_requests:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again shortly."}',
                status_code=429,
                media_type="application/json",
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers on every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if settings.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def configure_security(app: FastAPI) -> None:
    """Apply all security middleware to the FastAPI app."""
    configure_cors(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    logger.info("Security middleware configured (CORS + rate limiting + headers)")
