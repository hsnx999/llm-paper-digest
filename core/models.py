from pydantic import BaseModel
from typing import TypedDict, Optional, Literal, Any
from datetime import datetime


class PaperSummary(BaseModel):
    one_liner: str
    key_contributions: list[str]
    methodology: str
    why_it_matters: str
    limitations: str


class Paper(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str
    published_date: datetime
    categories: list[str]
    relevance_score: float = 0.0
    novelty_score: float = 0.0
    impact_score: float = 0.0
    final_score: float = 0.0
    rank: int = 0
    summary: Optional[PaperSummary] = None


class PipelineState(TypedDict):
    topics: list[str]
    categories: list[str]
    days_lookback: int
    top_n: int
    raw_papers: list[Paper]
    filtered_papers: list[Paper]
    summarised_papers: list[Paper]
    ranked_papers: list[Paper]
    report_paths: dict[str, str]
    errors: list[str]
    run_id: str
    started_at: datetime
    db: Optional[Any]


class DigestRun(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    paper_count: int = 0
    top_n: int = 10
    topics: list[str] = []
    categories: list[str] = []
    json_path: str = ""
    md_path: str = ""
    status: Literal["running", "success", "failed"] = "running"
