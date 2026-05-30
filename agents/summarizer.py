from __future__ import annotations

from loguru import logger

from core.llm_provider import get_llm
from core.models import Paper, PaperSummary, PipelineState
from core.rate_limiter import RateLimiter

_rate_limiter = RateLimiter()


def _build_user_prompt(paper: Paper) -> str:
    return (
        f"Title: {paper.title}\n"
        f"Authors: {', '.join(paper.authors)}\n"
        f"Abstract: {paper.abstract}\n"
        f"Categories: {', '.join(paper.categories)}\n\n"
        "Provide a structured summary of this paper."
    )


async def _summarise_single(paper: Paper) -> Paper:
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PaperSummary)
        await _rate_limiter.acquire(estimated_tokens=1000)
        result = await structured_llm.ainvoke([
            {
                "role": "system",
                "content": (
                    "You are a technical research summarizer. Write for a "
                    "time-pressed researcher. Be concrete — name specific "
                    "methods, datasets, and architectures. Do not inflate "
                    "importance. Be objective and precise."
                ),
            },
            {"role": "user", "content": _build_user_prompt(paper)},
        ])
        paper.summary = result
    except Exception:
        logger.warning("Failed to summarise paper '{}'", paper.title)
        paper.summary = None
    return paper


async def summarizer_node(state: PipelineState) -> PipelineState:
    papers = state["filtered_papers"]
    total = len(papers)
    summarised: list[Paper] = []

    for i, paper in enumerate(papers):
        result = await _summarise_single(paper)
        summarised.append(result)
        logger.info("Summarised {}/{} papers", i + 1, total)

    state["summarised_papers"] = summarised
    return state
