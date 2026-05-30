# LLM Paper Digest

An automated weekly pipeline that fetches, filters, summarises, and ranks the top ArXiv AI papers. Built for researchers who need signal, not noise.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Fetcher   │────▶│   Filter    │────▶│  Summarizer │────▶│   Ranker    │────▶│Report Gen    │
│  (arxiv)    │     │  (LLM)      │     │  (LLM)      │     │  (LLM)      │     │  (JSON+MD)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └──────────────┘
       │                   │                    │                    │                    │
       ▼                   ▼                    ▼                    ▼                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────────────────┐
  │                                     LangGraph StateGraph                                │
  └─────────────────────────────────────────────────────────────────────────────────────────┘
       │                                                                                    │
       ▼                                                                                    ▼
  ┌──────────┐                                                                     ┌──────────────┐
  │  SQLite  │                                                                     │   Streamlit  │
  │  (state) │                                                                     │   (UI)       │
  └──────────┘                                                                     └──────────────┘
```

The pipeline is composed of five stages chained via a LangGraph StateGraph:

1. **Fetcher** — Pulls recent papers from ArXiv by category.
2. **Filter** — Uses an LLM to filter papers by relevance to your topics.
3. **Summarizer** — Generates concise summaries of each relevant paper.
4. **Ranker** — Ranks papers by importance using an LLM.
5. **Report Generator** — Produces a final JSON digest and a formatted Markdown report.

All LLM calls (filter, summarise, rank) are rate-limited by a shared sliding-window limiter (30 req/min, 12K tokens/min) in `core/rate_limiter.py` to stay within Groq's free-tier constraints.

State is persisted in SQLite, and results are viewable through a Streamlit UI.

## Quick Start

```bash
git clone https://github.com/hsnx999/llm-paper-digest.git && cd llm-paper-digest
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit .env with your API key
streamlit run streamlit_app.py
```

To run the pipeline from the CLI instead of the UI:

```bash
python main.py run
python main.py history
python main.py export <run_id>
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Groq API key |
| `DEFAULT_TOPICS` | `large language models,agents,RAG,reasoning,multimodal` | Topics used for relevance filtering |
| `DEFAULT_CATEGORIES` | `cs.AI,cs.LG,cs.CL,cs.CV` | ArXiv categories to fetch from |
| `TOP_N_PAPERS` | `10` | Number of top-ranked papers in the final report |
| `DAYS_LOOKBACK` | `7` | How far back to look for new papers |
| `PAPERS_PER_RUN` | `60` | Max papers fetched per run |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Free-Tier Guide

This project uses **Groq's free inference endpoint** — no OpenAI key needed. All LLM calls (filtering, summarisation, ranking) cost **$0**.

1. Go to [groq.com](https://groq.com) and sign up (no credit card).
2. Generate an API key and set it in `.env`:

```
GROQ_API_KEY=gsk_your_actual_key
```

## Adding New ArXiv Categories

Edit the `DEFAULT_CATEGORIES` in your `.env` file. For example, to add multi-agent systems and robotics:

```
DEFAULT_CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV,cs.MA,cs.RO
```

The full list of ArXiv category IDs is available at [arxiv.org/category_taxonomy](https://arxiv.org/category_taxonomy).

## Scheduling Weekly Runs

### Cron

Run every Monday at 09:00:

```
0 9 * * 1 cd /path/to/llm-paper-digest && python main.py run
```

### GitHub Actions

Create `.github/workflows/weekly-digest.yml`:

```yaml
name: Weekly Digest

on:
  schedule:
    - cron: "0 9 * * 1"
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python main.py run
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: digest-report
          path: output/
```

Add `GROQ_API_KEY` to your repository secrets (Settings → Secrets and variables → Actions).

## CLI Reference

| Command | Description |
|---|---|
| `python main.py run` | Execute the full digest pipeline |
| `python main.py history` | List all past runs |
| `python main.py export <run_id>` | Print a past digest as Markdown |

The `run` command accepts optional overrides:

```
python main.py run --topics "LLMs,agents" --categories "cs.AI,cs.LG" --days 3 --top-n 5
```

## Project Structure

```
llm-paper-digest/
├── main.py                  # CLI entry point (typer)
├── streamlit_app.py         # Streamlit UI
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py      # LangGraph pipeline wiring
│   ├── fetcher.py           # ArXiv paper fetching
│   ├── filter.py            # LLM-based relevance filter
│   ├── summarizer.py        # LLM-based summarisation
│   ├── ranker.py            # LLM-based importance ranking
│   └── report_generator.py  # JSON + Markdown report output
├── core/
│   ├── __init__.py
│   ├── config.py            # Pydantic settings
│   ├── models.py            # Data models
│   ├── database.py          # SQLite persistence
│   ├── llm_provider.py      # LLM client wrapper
│   ├── rate_limiter.py      # 30 req/min + 12K TPM sliding window
│   └── vector_store.py      # FAISS + embeddings
├── pages/
│   ├── __init__.py
│   ├── 1_Dashboard.py       # Streamlit dashboard
│   ├── 2_Run_Pipeline.py    # Run pipeline UI
│   ├── 3_History.py         # Past runs browser
│   └── 4_Settings.py        # Settings page
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_pipeline.py
│   └── test_rate_limiter.py
├── output/                  # Generated reports (gitignored)
└── data/                    # SQLite DB, FAISS index (gitignored)
```
