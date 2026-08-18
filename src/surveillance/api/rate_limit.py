"""Single shared `Limiter` instance — defined separately from `main.py` so
route modules can apply `@limiter.limit(...)` to individual endpoints without
a circular import (docs/PLAN.md §5, rate limiting).

Applied per-route via the decorator, not `SlowAPIMiddleware`'s automatic
default-limits-for-everything: the installed slowapi's middleware walks
`app.routes` looking for plain `APIRoute` objects with `.endpoint`, but
FastAPI's `include_router` now wraps included routers in an internal
`_IncludedRouter` mount that has no `.endpoint` — so the middleware silently
finds no handler and treats every route as exempt. Confirmed directly: the
decorator form works with `include_router`, the middleware form does not.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from surveillance.settings import get_settings

limiter = Limiter(key_func=get_remote_address)
DEFAULT_RATE_LIMIT = f"{get_settings().rate_limit_per_minute}/minute"
