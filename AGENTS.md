# llm-paper-digest — Agent Instructions

## Quick start
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in GROQ_API_KEY
streamlit run streamlit_app.py
```

## Entrypoints
- `main.py` — CLI (typer): `run`, `history`, `export`
- `streamlit_app.py` — Streamlit UI, loads pages from `pages/`

## Architecture
- `agents/` are LangGraph **pipeline node functions** (async fns transforming a `PipelineState` TypedDict), not autonomous agents
- Graph wiring in `agents/orchestrator.py`: `build_graph()` → 5 nodes (`fetch → filter → summarise → rank → report`), conditional edge: if 0 papers fetched, skip to END
- Core entrypoint: `agents.orchestrator.run_pipeline()` — all other code imports from here

## State flow
`PipelineState` keys track progress through the graph:
```
raw_papers → filtered_papers → summarised_papers → ranked_papers → report_paths
```
Each node reads its input key and writes its output key.

## Config pitfalls
- `Config` uses Pydantic `BaseSettings` from `.env` — **must instantiate**: `Config().FIELD`, not `Config.FIELD` (class access raises `AttributeError`)
- Groq-only: `get_llm()` always returns `ChatGroq(model="llama-3.3-70b-versatile")`. No OpenAI path.
- `llm_provider.py` uses `logging`, rest of project uses `loguru`

## Tooling quirks
- **arxiv v2.x**: `arxiv.Client()` does NOT support context manager. Use `client = arxiv.Client(); list(client.results(search))`
- **Database**: SQLite, synchronous (no `await`). Auto-creates `data/digest.db` on init.
- **Vector store**: FAISS + `all-MiniLM-L6-v2` embeddings (free, no API key). Lives at `data/faiss_index/`.
- **Report output**: `output/digest_YYYY-MM-DD_{run_id[:8]}.json` and `.md`
- **Streamlit pages**: Loaded automatically by Streamlit from `pages/` — `1_Dashboard.py`, `2_Run_Pipeline.py`, `3_History.py`, `4_Settings.py`

## Commands
```bash
python main.py run                                              # defaults from .env
python main.py run --topics "RAG,agents" --days 3 --top-n 5    # overrides
python main.py history                                          # list past runs
python main.py export <run_id>                                  # print markdown
```

## No tests
No test framework, no test files. Verify manually via `python main.py run` or the Streamlit UI.

## LLM calls
All LLM calls use `with_structured_output(PydanticModel)` via Groq. Cost = $0. Summarizer adds 0.5s sleep between batches for rate limiting.

---

## Subagent architecture (build design)

This project was designed as a **multi-agent build** coordinated by an OrchestratorAgent. The 9 subagent domains and their file ownership:

| Subagent | Owns | Responsibility |
|---|---|---|
| **CoreInfra** | `core/{models,config,llm_provider,database,vector_store}.py` | Shared data models (Pydantic), `.env` config, Groq LLM factory, SQLite wrapper, FAISS vector store |
| **Fetcher** | `agents/fetcher.py` | ArXiv paper fetching, dedup against `seen_papers` table |
| **Filter** | `agents/filter.py` | Heuristic keyword pre-filter + LLM relevance scoring (batches of 10) |
| **Summarizer** | `agents/summarizer.py` | LLM summarization via `with_structured_output(PaperSummary)`, batches of 5, Groq rate-limit sleep |
| **Ranker** | `agents/ranker.py` | LLM novelty+impact scoring, weighted final score formula `0.40*relevance + 0.35*novelty + 0.25*impact` |
| **ReportGen** | `agents/report_generator.py` | JSON + Markdown report generation, trending topics extraction, executive summary LLM call |
| **Orchestrator** | `agents/orchestrator.py` | LangGraph `StateGraph` wiring, pipeline entrypoint, DB run lifecycle |
| **Streamlit** | `streamlit_app.py`, `pages/*.py` | Dark-themed Streamlit UI (dashboard, run pipeline, history, settings) |
| **CLI+Docs** | `main.py`, `requirements.txt`, `.env.example`, `README.md` | Typer CLI, dependency pins, env template, documentation |

### Shared contracts

All subagents coded against the same contracts in `core/`:
- **Models**: `Paper`, `PaperSummary`, `PipelineState`, `DigestRun` — the TypedDict state flows through every node
- **Config**: `Config()` singleton loaded from `.env` — all agents must use `Config().FIELD` (instance), not `Config.FIELD`
- **LLM**: `get_llm()` factory — agents call this, don't instantiate their own clients
- **Database**: `Database` singleton — agents call `is_seen`/`mark_seen`/`save_run`/`update_run`
- **Vector Store**: `VectorStore` — FAISS index at `data/faiss_index/`, used by Dashboard page

### Pipeline design decisions
- Each node is a pure async function `(PipelineState) -> PipelineState` — no side effects beyond writing state
- The LangGraph conditional edge (fetch → END if 0 papers) avoids wasting LLM tokens on empty runs
- Rate-limit safety: Groq gets 0.5s sleep between summarizer batches
- Error isolation: each node wraps its work in try/except, appends to `state["errors"]`, returns a safe partial state — never crashes the graph
- The `agents/` directory name is historic from the subagent build; the files are pipeline stages, not autonomous agents
