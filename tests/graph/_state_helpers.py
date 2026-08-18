from surveillance.graph.state import SurveillanceState, create_initial_state


def make_state(**overrides: object) -> SurveillanceState:
    """A full, valid SurveillanceState for node/edge unit tests, with only the
    fields under test overridden — real nodes always receive a complete state."""
    state = create_initial_state("ACC-1")
    return {**state, **overrides}  # type: ignore[typeddict-item]
