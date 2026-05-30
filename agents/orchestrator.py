from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph

from agents.fetcher import fetcher_node
from agents.filter import filter_node
from agents.ranker import ranker_node
from agents.report_generator import report_generator_node
from agents.summarizer import summarizer_node
from core.config import Config
from core.database import Database
from core.models import DigestRun, PipelineState
from loguru import logger


def build_graph() -> CompiledGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("fetch", fetcher_node)
    graph.add_node("filter", filter_node)
    graph.add_node("summarise", summarizer_node)
    graph.add_node("rank", ranker_node)
    graph.add_node("report", report_generator_node)

    graph.set_entry_point("fetch")

    graph.add_edge("filter", "summarise")
    graph.add_edge("summarise", "rank")
    graph.add_edge("rank", "report")
    graph.add_edge("report", END)

    graph.add_conditional_edges(
        "fetch",
        lambda state: "filter" if state["raw_papers"] else END,
    )

    return graph.compile()


async def run_pipeline(
    topics: list[str] | None = None,
    categories: list[str] | None = None,
    days_lookback: int | None = None,
    top_n: int | None = None,
) -> PipelineState:
    config = Config()

    initial_state: PipelineState = {
        "topics": topics or config.effective_topics,
        "categories": categories or config.effective_categories,
        "days_lookback": days_lookback or config.DAYS_LOOKBACK,
        "top_n": top_n or config.TOP_N_PAPERS,
        "raw_papers": [],
        "filtered_papers": [],
        "summarised_papers": [],
        "ranked_papers": [],
        "report_paths": {},
        "errors": [],
        "run_id": str(uuid4()),
        "started_at": datetime.now(timezone.utc),
    }

    db = Database()
    run_record = DigestRun(
        run_id=initial_state["run_id"],
        started_at=initial_state["started_at"],
        top_n=initial_state["top_n"],
        topics=initial_state["topics"],
        categories=initial_state["categories"],
        status="running",
    )
    db.save_run(run_record)

    logger.info(f"Starting pipeline run {initial_state['run_id']}")
    logger.info(f"Topics: {initial_state['topics']}")
    logger.info(f"Categories: {initial_state['categories']}")

    graph = build_graph()
    result = await graph.ainvoke(initial_state)

    ranked = result.get("ranked_papers", [])
    paths = result.get("report_paths", {})

    db.update_run(DigestRun(
        run_id=result["run_id"],
        started_at=result["started_at"],
        finished_at=datetime.utcnow(),
        paper_count=len(ranked),
        top_n=result["top_n"],
        topics=result["topics"],
        categories=result["categories"],
        json_path=paths.get("json", ""),
        md_path=paths.get("markdown", ""),
        status="success" if not result.get("errors") else "failed",
    ))

    n_fetched = len(result.get("raw_papers", []))
    n_ranked = len(ranked)
    logger.info(f"Pipeline completed: {n_fetched} fetched, {n_ranked} ranked")
    if result.get("errors"):
        logger.warning(f"Pipeline completed with {len(result['errors'])} errors")

    return result
