from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from surveillance.api.deps import get_run_store
from surveillance.api.middleware import MaxBodySizeMiddleware
from surveillance.api.rate_limit import limiter
from surveillance.api.routes import health, investigations
from surveillance.observability import configure_logging
from surveillance.settings import Settings, get_settings

_LOCALHOST_ORIGIN = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


def cors_options(config: Settings) -> dict[str, object]:
    """Configured origins only; development also trusts any localhost port,
    because `next dev` moves to :3001 when :3000 is taken."""
    options: dict[str, object] = {
        "allow_origins": config.frontend_origins,
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"],
    }
    if config.environment == "development":
        options["allow_origin_regex"] = _LOCALHOST_ORIGIN
    return options


settings = get_settings()
configure_logging(settings.environment)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_run_store().fail_interrupted_runs("interrupted by a server restart")
    yield


app = FastAPI(title="Trade Surveillance Agent", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(MaxBodySizeMiddleware, max_body_bytes=settings.max_request_body_bytes)
# Added last so it is the outermost layer and answers preflights first.
app.add_middleware(CORSMiddleware, **cors_options(settings))  # type: ignore[arg-type]

app.include_router(health.router)
app.include_router(investigations.router)
