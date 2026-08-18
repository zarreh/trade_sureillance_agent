from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from surveillance.graph.nodes.done import done_node
from surveillance.graph.nodes.echo import echo_node
from surveillance.graph.state import SkeletonState

SkeletonGraph = CompiledStateGraph[SkeletonState, None, SkeletonState, SkeletonState]


def build_skeleton_graph() -> SkeletonGraph:
    """The only function that wires nodes and edges. Phase 0: echo -> done."""
    workflow = StateGraph(SkeletonState)
    workflow.add_node("echo", echo_node)
    workflow.add_node("done", done_node)
    workflow.set_entry_point("echo")
    workflow.add_edge("echo", "done")
    workflow.add_edge("done", END)
    return workflow.compile()
