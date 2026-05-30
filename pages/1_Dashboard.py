import json
import glob as glob_mod
import os
import streamlit as st
from core.database import Database
from core.config import Config
from core.models import Paper
from core.vector_store import VectorStore

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .search-header { color: #e8e8e8; font-size: 1.8rem; font-weight: 600; margin-bottom: 0.5rem; }
    .paper-score { font-size: 1.1rem; font-weight: 700; color: #4fc3f7; }
    .paper-rank { font-size: 0.9rem; color: #9b9b9b; }
    .section-label { color: #9b9b9b; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.8rem; }
    .section-content { color: #d4d4d4; font-size: 0.95rem; }
    .section-content ul { margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)


def load_latest_digest():
    output_dir = Config().OUTPUT_DIR
    pattern = os.path.join(output_dir, "digest_*.json")
    files = glob_mod.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    with open(latest) as f:
        data = json.load(f)
    return data


def papers_from_digest(data) -> list[Paper]:
    raw = data if isinstance(data, list) else data.get("papers", data.get("ranked_papers", []))
    papers = []
    for p in raw:
        try:
            papers.append(Paper(**p) if not isinstance(p, Paper) else p)
        except Exception:
            continue
    return papers


db = Database()
config = Config()

with st.spinner("Loading digest data..."):
    data = load_latest_digest()
    all_papers = papers_from_digest(data) if data else []

all_categories = sorted({cat for p in all_papers for cat in p.categories})
all_dates = sorted({p.published_date.date() for p in all_papers if p.published_date})

with st.sidebar:
    st.markdown("### Filters")

    selected_categories = st.multiselect(
        "Categories",
        options=all_categories,
        default=list(all_categories),
    )

    min_score = st.slider(
        "Min Score",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.1,
    )

    if all_dates:
        min_date = all_dates[0]
        max_date = all_dates[-1]
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

st.markdown(
    '<p class="search-header">📄 Digest Dashboard</p>',
    unsafe_allow_html=True,
)

search_query = st.text_input(
    "Search papers",
    placeholder="Type a query and press Enter to search semantically...",
    label_visibility="collapsed",
)

if search_query:
    vs = VectorStore()
    if vs.load():
        search_results = vs.search(search_query, k=10)
    else:
        search_results = []
else:
    search_results = None

if search_results is not None:
    display_papers = search_results
    header_text = f'🔍 Search Results for "{search_query}"'
else:
    display_papers = all_papers
    header_text = "📄 All Papers"

st.markdown("### 📊 Trends")

db_for_charts = Database()
all_runs = db_for_charts.get_all_runs()
if len(all_runs) >= 2:
    chart_data = [
        {"Date": r.started_at.strftime("%Y-%m-%d"), "Papers": r.paper_count}
        for r in reversed(all_runs)
        if r.paper_count > 0
    ]
    if chart_data:
        st.line_chart(
            chart_data,
            x="Date",
            y="Papers",
            use_container_width=True,
            height=250,
        )
elif len(all_runs) == 1:
    st.caption(f"One run completed so far ({all_runs[0].paper_count} papers). More runs needed for trends.")
else:
    st.caption("No run data yet. Run the pipeline to see trends.")

if not display_papers and not all_papers:
    st.info("No digest data found. Run the pipeline from the Run Pipeline page first.")
    st.stop()

filtered = []
for p in display_papers:
    if selected_categories and not any(c in selected_categories for c in p.categories):
        continue
    if p.final_score < min_score:
        continue
    if date_range and p.published_date:
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            d = p.published_date.date()
            if d < date_range[0] or d > date_range[1]:
                continue
    filtered.append(p)

if not filtered and search_results is not None and all_papers:
    st.info("No search results match your current filters.")
    st.stop()

filtered.sort(key=lambda x: x.final_score, reverse=True)

st.markdown(f"**{len(filtered)}** papers displayed")

for p in filtered:
    with st.expander(f"#{p.rank} — {p.title}", expanded=False):
        col_left, col_right = st.columns([4, 1])
        with col_left:
            st.markdown(p.summary.one_liner if p.summary else p.abstract)
        with col_right:
            st.markdown(
                f'<div class="paper-score">Score: {p.final_score:.1f}</div>',
                unsafe_allow_html=True,
            )

        if p.summary:
            st.markdown('<div class="section-label">Key Contributions</div>', unsafe_allow_html=True)
            for c in p.summary.key_contributions:
                st.markdown(f'<div class="section-content">• {c}</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-label">Methodology</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="section-content">{p.summary.methodology}</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="section-label">Why It Matters</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="section-content">{p.summary.why_it_matters}</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="section-label">Limitations</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="section-content">{p.summary.limitations}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.link_button("🔗 View on ArXiv", p.url, use_container_width=True)
        with col_btn2:
            st.link_button("📄 View PDF", p.pdf_url, use_container_width=True)
