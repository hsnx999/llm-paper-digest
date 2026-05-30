import pytest
from agents.orchestrator import build_graph
from core.models import PipelineState


class TestPipeline:
    def test_graph_compiles(self):
        graph = build_graph()
        assert graph is not None
        assert hasattr(graph, "ainvoke")

    def test_graph_has_correct_nodes(self):
        graph = build_graph()
        expected = {"fetch", "filter", "summarise", "rank", "report"}
        assert expected.issubset(set(graph.nodes.keys()))

    def test_conditional_edge_exists(self):
        graph = build_graph()
        assert "fetch" in graph.builder.branches
