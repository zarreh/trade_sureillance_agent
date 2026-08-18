from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from surveillance.api.routes import health, investigations
from surveillance.observability import configure_logging
from surveillance.settings import get_settings

settings = get_settings()
configure_logging(settings.environment)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

app = FastAPI(title="Trade Surveillance Agent", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(health.router)
app.include_router(investigations.router)
