"""Logging is provided by `zarreh_agentkit.observability` (extracted substrate);
this module re-exports it so existing `surveillance.observability` imports keep
working."""

from zarreh_agentkit.observability import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
