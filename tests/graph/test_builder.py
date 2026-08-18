from surveillance.graph.builder import build_skeleton_graph


def test_skeleton_graph_runs_to_completion() -> None:
    graph = build_skeleton_graph()
    result = graph.invoke({"message": "hello", "echoed": "", "done": False})
    assert result["echoed"] == "echo: hello"
    assert result["done"] is True
