from __future__ import annotations

import asyncio

from loguru import logger

from core.config import Config
from core.llm_provider import get_llm
from core.models import Paper, PaperSummary, PipelineState


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
    batch_size = 5
    summarised: list[Paper] = []

    for batch_start in range(0, total, batch_size):
        batch = papers[batch_start : batch_start + batch_size]
        results = await asyncio.gather(
            *(_summarise_single(p) for p in batch)
        )
        summarised.extend(results)

        done = len(summarised)
        logger.info("Summarised {}/{} papers", done, total)

        if Config().LLM_PROVIDER == "groq":
            await asyncio.sleep(0.5)

    state["summarised_papers"] = summarised
    return state
