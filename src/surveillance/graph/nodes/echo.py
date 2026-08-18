from surveillance.graph.state import SkeletonState


def echo_node(state: SkeletonState) -> dict[str, str]:
    """Repeats the input back — proves state flows through the compiled graph."""
    return {"echoed": f"echo: {state['message']}"}
