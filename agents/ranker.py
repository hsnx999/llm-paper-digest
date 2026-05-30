from __future__ import annotations

import asyncio

from core.llm_provider import get_llm
from core.models import Paper, PipelineState
from core.rate_limiter import RateLimiter
from loguru import logger
from pydantic import BaseModel


_rate_limiter = RateLimiter()


class PaperScores(BaseModel):
    novelty: float
    impact: float


SYSTEM_PROMPT = (
    "You are a research quality evaluator. Rate each paper on two axes "
    "(both 0–10): novelty (how surprising/novel vs existing literature) "
    "and impact (practical/applied significance). Be critical and objective."
)


def _build_user_prompt(paper: Paper) -> str:
    summary_text = paper.summary if paper.summary else "Summary not available."
    return (
        f"Title: {paper.title}\n\n"
        f"Abstract: {paper.abstract}\n\n"
        f"Summary: {summary_text}"
    )


def _compute_final_score(
    relevance_score: float, novelty: float, impact: float
) -> float:
    return 0.40 * relevance_score + 0.35 * novelty + 0.25 * impact


async def _score_paper(paper: Paper) -> PaperScores | None:
    llm = get_llm()
    structured_llm = llm.with_structured_output(PaperScores)
    try:
        await _rate_limiter.acquire(estimated_tokens=700)
        result: PaperScores = await structured_llm.ainvoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(paper)},
            ]
        )
        logger.info(
            "Scored paper={} novelty={} impact={}",
            paper.title,
            result.novelty,
            result.impact,
        )
        return result
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "rate_limit" in err_msg.lower():
            logger.warning("Rate limited, retrying once paper={}", paper.title)
            try:
                await asyncio.sleep(5)
                result = await structured_llm.ainvoke(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(paper)},
                    ]
                )
                logger.info(
                    "Scored paper={} novelty={} impact={} (retry)",
                    paper.title,
                    result.novelty,
                    result.impact,
                )
                return result
            except Exception:
                logger.warning("Failed to score paper={} after retry", paper.title)
                return None
        logger.warning("Failed to score paper={} error={}", paper.title, exc)
        return None


async def ranker_node(state: PipelineState) -> PipelineState:
    papers: list[Paper] = state["summarised_papers"]
    top_n: int = state["top_n"]

    ranked: list[Paper] = []
    for paper in papers:
        scores = await _score_paper(paper)
        if scores is not None:
            paper.novelty_score = scores.novelty
            paper.impact_score = scores.impact
            final_score = _compute_final_score(
                paper.relevance_score, scores.novelty, scores.impact
            )
        else:
            final_score = paper.relevance_score * 0.4
        paper.final_score = final_score
        ranked.append(paper)

    ranked.sort(key=lambda p: p.final_score, reverse=True)
    for idx, paper in enumerate(ranked, start=1):
        paper.rank = idx

    ranked = ranked[:top_n]

    logger.info(
        "Ranked {} papers, kept top {}", len(papers), len(ranked)
    )

    state["ranked_papers"] = ranked
    return state
