from __future__ import annotations

import asyncio
import random

from loguru import logger

from core.llm_provider import get_llm
from core.models import Paper, PaperSummary, PipelineState
from core.rate_limiter import rate_limiter

def _build_user_prompt(paper: Paper) -> str:
    return (
        f"Title: {paper.title}\n"
        f"Authors: {', '.join(paper.authors)}\n"
        f"Abstract: {paper.abstract}\n"
        f"Categories: {', '.join(paper.categories)}\n\n"
        "Provide a structured summary of this paper."
    )


async def _summarise_single(paper: Paper, structured_llm) -> Paper:
    try:
        await rate_limiter.acquire(estimated_tokens=1000)
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
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "rate_limit" in err_msg.lower():
            logger.warning("Rate limited, retrying once paper='{}'", paper.title)
            try:
                await asyncio.sleep(random.uniform(5, 10))
                await rate_limiter.acquire(estimated_tokens=1000)
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
                logger.warning("Failed to summarise paper '{}' after retry", paper.title)
                paper.summary = None
        else:
            logger.warning("Failed to summarise paper '{}': {}", paper.title, exc)
            paper.summary = None
    return paper


async def summarizer_node(state: PipelineState) -> PipelineState:
    try:
        papers = state["filtered_papers"]
        total = len(papers)
        batch_size = 5
        summarised: list[Paper] = []

        llm = get_llm()
        structured_llm = llm.with_structured_output(PaperSummary)

        for batch_start in range(0, total, batch_size):
            batch = papers[batch_start : batch_start + batch_size]
            results = await asyncio.gather(
                *(_summarise_single(p, structured_llm) for p in batch),
                return_exceptions=True,
            )
            for paper, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.warning("Summarize failed for '{}': {}", paper.title, result)
                    state["errors"].append(f"summarizer: failed for {paper.title}: {result}")
                    paper.summary = None
                    summarised.append(paper)
                elif paper.summary is None:
                    state["errors"].append(f"summarizer: summarisation failed for {paper.title}")
                    summarised.append(paper)
                else:
                    summarised.append(result)
            done = len(summarised)
            logger.info("Summarised {}/{} papers", done, total)

        state["summarised_papers"] = summarised
    except Exception as e:
        logger.error("Summarizer node failed: {}", e)
        state["errors"].append(f"summarizer_node: {e}")
        state["summarised_papers"] = state.get("summarised_papers", [])
    return state
