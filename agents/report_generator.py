from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os

from core.config import Config
from core.llm_provider import get_llm
from core.models import Paper, PipelineState
from core.rate_limiter import rate_limiter
from loguru import logger

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


STOPWORDS = ENGLISH_STOP_WORDS


def _get_trending_topics(papers: list[Paper], top_n: int = 10) -> list[tuple[str, int]]:
    word_counts: dict[str, int] = {}
    for paper in papers:
        for word in paper.title.lower().split():
            word = word.strip(".,!?;:'\"()[]{}")
            if word and word not in STOPWORDS and len(word) > 2:
                word_counts[word] = word_counts.get(word, 0) + 1
    return sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]


def _compute_week_range(state: PipelineState) -> tuple[str, str]:
    started_at: datetime = state["started_at"]
    days_lookback: int = state["days_lookback"]
    end_date = started_at.strftime("%Y-%m-%d")
    start_date = (started_at - timedelta(days=days_lookback)).strftime("%Y-%m-%d")
    return start_date, end_date


async def _generate_executive_summary(papers: list[Paper], topics: list[str], n: int) -> str:
    if not papers:
        return "No papers were available for this week's digest."
    paper_lines = "\n".join(
        f"- {p.title}: {p.summary.one_liner if p.summary else p.abstract[:200]}"
        for p in papers
    )
    prompt = (
        f"Summarize the key themes and trends from this week's top {n} papers on {topics}.\n\n"
        f"Papers:\n{paper_lines}\n\n"
        "Write one paragraph (3-5 sentences). Focus on what's new, what's trending, and what's important."
    )
    try:
        model = get_llm()
        await rate_limiter.acquire(estimated_tokens=300)
        response = await model.ainvoke([
            {"role": "system", "content": "You are a research paper digest writer."},
            {"role": "user", "content": prompt},
        ])
        return response.content
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate_limit" in err_str.lower():
            logger.warning("Executive summary rate limited, original error: {}", e)
            await asyncio.sleep(10)
            await rate_limiter.acquire(estimated_tokens=300)
            try:
                model2 = get_llm()
                response = await model2.ainvoke([
                    {"role": "system", "content": "You are a research paper digest writer."},
                    {"role": "user", "content": prompt},
                ])
                return response.content
            except Exception as retry_err:
                logger.warning("Executive summary retry also failed: {}", retry_err)
        logger.error(f"Executive summary generation failed: {e}")
        return (
            "This week's papers cover a range of topics in the specified areas, "
            "with notable contributions advancing the field."
        )


def _build_json_report(state: PipelineState, papers: list[Paper]) -> dict:
    return {
        "run_id": state["run_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topics": state["topics"],
        "categories": state["categories"],
        "paper_count": len(papers),
        "papers": [paper.model_dump(mode="json") for paper in papers],
    }


def _build_markdown_report(
    state: PipelineState,
    papers: list[Paper],
    start_date: str,
    end_date: str,
    total_fetched: int,
    executive_summary: str,
    trending_topics: list[tuple[str, int]],
) -> str:
    categories_str = ", ".join(state["categories"])
    lines: list[str] = [
        f"# LLM Paper Digest \u2014 Week of {start_date} to {end_date}",
        "",
        f"> {len(papers)} papers ranked from {total_fetched} fetched across {categories_str}.",
        "",
        "## Executive Summary",
        executive_summary,
        "",
        "## Top Papers",
        "",
    ]
    for paper in papers:
        if not paper.summary:
            continue
        authors_str = ", ".join(paper.authors)
        contributions = "\n".join(f"- {c}" for c in paper.summary.key_contributions)
        lines.extend([
            f"### {paper.rank}. {paper.title} `[score: {paper.final_score:.2f}]`",
            "",
            f"**TL;DR:** {paper.summary.one_liner}",
            "",
            f"**Authors:** {authors_str}",
            "",
            f"**ArXiv:** {paper.url}",
            "",
            "**Key Contributions:**",
            contributions,
            "",
            f"**Methodology:** {paper.summary.methodology}",
            "",
            f"**Why it matters:** {paper.summary.why_it_matters}",
            "",
            f"**Limitations:** {paper.summary.limitations}",
            "",
            "---",
            "",
        ])
    lines.append("## Trending Topics This Week")
    lines.append("")
    for word, count in trending_topics:
        lines.append(f"- {word}: {count}")
    lines.append("")
    return "\n".join(lines)


async def report_generator_node(state: PipelineState) -> PipelineState:
    cfg = Config()
    output_dir = os.path.expanduser(cfg.OUTPUT_DIR)
    try:
        os.makedirs(output_dir, exist_ok=True)

        papers: list[Paper] = state.get("ranked_papers", [])
        topics: list[str] = state["topics"]
        total_fetched = len(state.get("raw_papers", []))

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        run_id = state["run_id"]
        run_id_short = run_id[:8]

        json_filename = f"digest_{date_str}_{run_id_short}.json"
        md_filename = f"digest_{date_str}_{run_id_short}.md"

        json_path = os.path.join(output_dir, json_filename)
        md_path = os.path.join(output_dir, md_filename)

        start_date, end_date = _compute_week_range(state)
        filtered_papers = state.get("filtered_papers", [])
        trending = _get_trending_topics(filtered_papers or papers)
        executive_summary = await _generate_executive_summary(papers, topics, len(papers))

        json_data = _build_json_report(state, papers)
        md_content = _build_markdown_report(
            state, papers, start_date, end_date, total_fetched, executive_summary, trending,
        )

        report_paths = {}
        try:
            with open(json_path, "w") as f:
                json.dump(json_data, f, indent=2)
            report_paths["json"] = json_path
            logger.info(f"JSON report written to {json_path}")
        except Exception as e:
            logger.error(f"Failed to write JSON report: {e}")

        try:
            with open(md_path, "w") as f:
                f.write(md_content)
            report_paths["markdown"] = md_path
            logger.info(f"Markdown report written to {md_path}")
        except Exception as e:
            logger.error(f"Failed to write Markdown report: {e}")

        if state.get("db") and report_paths:
            from core.models import DigestRun
            state["db"].update_run(DigestRun(
                run_id=state["run_id"],
                started_at=state["started_at"],
                finished_at=datetime.now(timezone.utc),
                paper_count=len(papers),
                top_n=state.get("top_n", Config().TOP_N_PAPERS),
                topics=state["topics"],
                categories=state["categories"],
                json_path=report_paths.get("json", ""),
                md_path=report_paths.get("markdown", ""),
                status="success",
            ))

        state["report_paths"] = report_paths
    except Exception as e:
        logger.error("Report generator node failed: {}", e)
        state["errors"].append(f"report_generator_node: {e}")
        state["report_paths"] = state.get("report_paths", {})
    return state
