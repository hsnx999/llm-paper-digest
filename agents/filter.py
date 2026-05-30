from __future__ import annotations

import asyncio

from core.models import Paper, PipelineState
from core.llm_provider import get_llm
from core.rate_limiter import rate_limiter
from loguru import logger
from pydantic import BaseModel


class PaperScore(BaseModel):
    id: str
    relevance: float
    reasoning: str


class RelevanceBatch(BaseModel):
    scores: list[PaperScore]


async def filter_node(state: PipelineState) -> PipelineState:
    raw_papers: list[Paper] = state["raw_papers"]
    topics: list[str] = state["topics"]

    logger.info(f"Filtering {len(raw_papers)} papers...")

    # 1. Heuristic pre-filter: drop papers with no topic match in title or abstract
    surviving: list[Paper] = []
    for paper in raw_papers:
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        if any(topic.lower() in title_lower or topic.lower() in abstract_lower for topic in topics):
            surviving.append(paper)

    dropped = len(raw_papers) - len(surviving)
    if dropped:
        logger.info(f"Heuristic filter dropped {dropped} off-topic papers")

    # 2. LLM relevance scoring in batches of 10
    model = get_llm()
    structured = model.with_structured_output(RelevanceBatch)

    system_prompt = (
        "You are a research paper relevance classifier. "
        f"The user is interested in the following topics: {topics}. "
        "Score each paper's relevance to these topics from 0 to 10. "
        "Be strict — 10 means perfectly on-topic, 0 means completely irrelevant. "
        "Provide a brief reasoning for each score."
    )

    scored_papers: list[Paper] = []

    for i in range(0, len(surviving), 10):
        batch = surviving[i : i + 10]
        batch_repr = [
            {
                "id": p.id,
                "title": p.title,
                "abstract": p.abstract,
            }
            for p in batch
        ]

        try:
            await rate_limiter.acquire(estimated_tokens=3500)
            result: RelevanceBatch = await structured.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Score these papers:\n{batch_repr}"},
            ])
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                logger.warning("Rate limited on filter batch, retrying once after delay")
                await asyncio.sleep(5)
                try:
                    await rate_limiter.acquire(estimated_tokens=3500)
                    result = await structured.ainvoke([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Score these papers:\n{batch_repr}"},
                    ])
                except Exception as retry_err:
                    logger.error(f"Filter batch scoring retry also failed: {retry_err}")
                    state["errors"].append(f"filter: batch {i} scoring failed after retry: {retry_err}")
                    for paper in batch:
                        paper.relevance_score = 5.0
                        scored_papers.append(paper)
                    continue
            else:
                logger.error(f"LLM batch scoring failed for batch starting at index {i}: {e}")
                state["errors"].append(f"filter: batch {i} scoring failed: {e}")
                for paper in batch:
                    paper.relevance_score = 5.0
                    scored_papers.append(paper)
                continue

        id_to_score: dict[str, PaperScore] = {}
        for s in result.scores:
            if s.id in id_to_score:
                logger.warning(f"Duplicate score for paper {s.id}; using first")
            else:
                id_to_score[s.id] = s

        if len(id_to_score) != len(batch):
            missing = [p.id for p in batch if p.id not in id_to_score]
            logger.warning(f"LLM returned {len(id_to_score)} scores for {len(batch)} papers; missing: {missing}")
            state["errors"].append(
                f"filter: LLM returned {len(id_to_score)}/{len(batch)} scores"
            )

        for paper in batch:
            if paper.id in id_to_score:
                paper.relevance_score = id_to_score[paper.id].relevance
            else:
                logger.warning(f"Paper {paper.id} missing from LLM scores; assigning neutral 5.0")
                paper.relevance_score = 5.0
            scored_papers.append(paper)

    # 4. Keep papers with score >= 5.0
    filtered = [p for p in scored_papers if p.relevance_score >= 5.0]

    logger.info(f"LLM filter kept {len(filtered)}/{len(scored_papers)} papers")

    state["filtered_papers"] = filtered
    return state
