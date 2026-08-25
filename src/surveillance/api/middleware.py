"""Re-export of `zarreh_agentkit.api.middleware` (extracted substrate).

Enforces a maximum request body size at the ASGI level (docs/PLAN.md §5,
OWASP API4:2023). See the package for the implementation.
"""

from zarreh_agentkit.api.middleware import MaxBodySizeMiddleware

__all__ = ["MaxBodySizeMiddleware"]
