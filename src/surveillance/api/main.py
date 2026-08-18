from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from surveillance.api.middleware import MaxBodySizeMiddleware
from surveillance.api.rate_limit import limiter
from surveillance.api.routes import health, investigations
from surveillance.observability import configure_logging
from surveillance.settings import get_settings

settings = get_settings()
configure_logging(settings.environment)

app = FastAPI(title="Trade Surveillance Agent", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(MaxBodySizeMiddleware, max_body_bytes=settings.max_request_body_bytes)

app.include_router(health.router)
app.include_router(investigations.router)
