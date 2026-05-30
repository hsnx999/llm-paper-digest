from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import arxiv

from core.config import Config
from core.models import Paper, PipelineState
from loguru import logger


def _run_arxiv_search(client: arxiv.Client, query: str, max_results: int) -> list[arxiv.Result]:
    search = arxiv.Search(query=query, max_results=max_results)
    return list(client.results(search))


async def fetcher_node(state: PipelineState) -> PipelineState:
    try:
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=state["days_lookback"])
        date_fmt = "%Y%m%d"
        start_str = start_date.strftime(date_fmt)
        end_str = today.strftime(date_fmt)

        paper_map: dict[str, Paper] = {}
        total_wanted = Config().PAPERS_PER_RUN
        client = arxiv.Client()

        for category in state["categories"]:
            query = f"cat:{category} AND submittedDate:[{start_str} TO {end_str}]"
            logger.info("Querying arXiv for category: {}", category)
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(_run_arxiv_search, client, query, total_wanted),
                    timeout=30.0,
                )
                for r in results:
                    arxiv_id = r.get_short_id().split("v")[0]
                    if arxiv_id not in paper_map:
                        paper_map[arxiv_id] = Paper(
                            id=arxiv_id,
                            title=r.title,
                            authors=[a.name for a in r.authors],
                            abstract=r.summary,
                            url=r.entry_id,
                            pdf_url=r.pdf_url,
                            published_date=r.published,
                            categories=list(r.categories),
                        )
            except Exception as exc:
                logger.warning("Failed to fetch category {}: {}", category, exc)
                state["errors"].append(f"arXiv query failed for {category}: {exc}")

        for topic in state["topics"]:
            query = f'"{topic}" AND submittedDate:[{start_str} TO {end_str}]'
            logger.info("Querying arXiv for topic: {}", topic)
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(_run_arxiv_search, client, query, total_wanted),
                    timeout=30.0,
                )
                for r in results:
                    arxiv_id = r.get_short_id().split("v")[0]
                    if arxiv_id not in paper_map:
                        paper_map[arxiv_id] = Paper(
                            id=arxiv_id,
                            title=r.title,
                            authors=[a.name for a in r.authors],
                            abstract=r.summary,
                            url=r.entry_id,
                            pdf_url=r.pdf_url,
                            published_date=r.published,
                            categories=list(r.categories),
                        )
            except Exception as exc:
                logger.warning("Failed to fetch topic {}: {}", topic, exc)
                state["errors"].append(f"arXiv query failed for {topic}: {exc}")

        all_ids = list(paper_map.keys())
        unseen_ids = [pid for pid in all_ids if not state["db"].is_seen(pid)]
        unseen_papers = [paper_map[pid] for pid in unseen_ids]

        if unseen_ids:
            state["db"].mark_seen(unseen_ids)

        state["raw_papers"] = unseen_papers[:total_wanted]

        logger.info(
            "Fetched {} new papers ({} total candidates, {} already seen)",
            len(state["raw_papers"]),
            len(paper_map),
            len(all_ids) - len(unseen_ids),
        )

    except Exception:
        logger.exception("Failed to fetch papers from arXiv")
        state["errors"] = state.get("errors", []) + ["arXiv fetch failed"]
        state["raw_papers"] = []

    return state
