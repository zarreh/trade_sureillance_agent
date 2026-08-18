from functools import lru_cache
from pathlib import Path

from surveillance.graph.builder import SkeletonGraph, SurveillanceGraph, build_skeleton_graph
from surveillance.graph.builder import build_surveillance_graph as _build_surveillance_graph
from surveillance.settings import Settings, get_settings
from surveillance.store.run_store import RunStore


def settings_dependency() -> Settings:
    return get_settings()


@lru_cache
def get_compiled_graph() -> SkeletonGraph:
    """Single compiled-graph instance, shared across requests."""
    return build_skeleton_graph()


@lru_cache
def get_surveillance_graph() -> SurveillanceGraph:
    """Single compiled real investigation graph, shared across requests.
    Overridden in tests via `app.dependency_overrides` so a request can be
    served without a live LLM or a real facts.db."""
    return _build_surveillance_graph(get_settings())


@lru_cache
def get_run_store() -> RunStore:
    return RunStore(Path(get_settings().run_store_path))
