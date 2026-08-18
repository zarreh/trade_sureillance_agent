from surveillance.graph.state import SkeletonState


def done_node(state: SkeletonState) -> dict[str, bool]:
    """Terminal node — proves a graph can run to completion end to end."""
    return {"done": True}
