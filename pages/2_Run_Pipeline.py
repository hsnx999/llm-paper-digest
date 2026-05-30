import asyncio
import time
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from core.database import Database
from core.config import Config
from core.vector_store import VectorStore
from agents.orchestrator import run_pipeline
from core.models import Paper

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .run-header { color: #e8e8e8; font-size: 1.8rem; font-weight: 600; }
    .summary-stat { color: #d4d4d4; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

config = Config()
db = Database()

st.markdown(
    '<p class="run-header">▶ Run Pipeline</p>',
    unsafe_allow_html=True,
)

topics_str = ", ".join(config.effective_topics)

with st.form("pipeline_form"):
    topics = st.text_input(
        "Topics",
        value=topics_str,
        placeholder="e.g. large language models,agents,RAG",
    )

    categories = st.multiselect(
        "Categories",
        options=["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.MA", "cs.RO", "cs.NE"],
        default=config.effective_categories,
    )

    col1, col2 = st.columns(2)
    with col1:
        days_lookback = st.slider(
            "Days Lookback",
            min_value=1,
            max_value=30,
            value=config.DAYS_LOOKBACK,
        )
    with col2:
        top_n = st.slider(
            "Top N Papers",
            min_value=5,
            max_value=30,
            value=config.TOP_N_PAPERS,
        )

    submitted = st.form_submit_button("▶ Run Pipeline", use_container_width=True, type="primary")

if submitted:
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]

    status_placeholder = st.status("Pipeline running...", expanded=True)
    progress_bar = st.progress(0, text="Starting...")

    if "cancel_pipeline" not in st.session_state:
        st.session_state.cancel_pipeline = False

    cancel_col = st.columns([1, 5, 1])[1]
    with cancel_col:
        st.button("✋ Cancel", key="cancel_btn", use_container_width=True,
                  on_click=lambda: setattr(st.session_state, "cancel_pipeline", True))

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                run_pipeline(
                    topics=topic_list,
                    categories=categories,
                    days_lookback=days_lookback,
                    top_n=top_n,
                )
            )
            return result
        finally:
            loop.close()

    start = time.time()
    status_phases = ["Fetching papers...", "Filtering...", "Summarising...", "Ranking...", "Generating report..."]

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run)
        phase = 0
        while not future.done():
            if st.session_state.cancel_pipeline:
                status_placeholder.update(label="Pipeline cancelled", state="error", expanded=False)
                st.warning("Pipeline was cancelled.")
                st.stop()
            elapsed = int(time.time() - start)
            phase = min(elapsed // 30, len(status_phases) - 1)
            progress = min(elapsed / 180, 0.95)
            progress_bar.progress(progress, text=f"{status_phases[phase]} ({elapsed}s)")
            time.sleep(0.5)

    progress_bar.progress(1.0, text="Complete!")
    result = future.result()
    elapsed = time.time() - start

    errors = result.get("errors", [])
    ranked = result.get("ranked_papers", [])
    raw = result.get("raw_papers", [])
    paths = result.get("report_paths", {})

    status_placeholder.update(
        label="Pipeline complete!",
        state="complete" if not errors else "error",
        expanded=False,
    )

    st.success("Pipeline finished successfully!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Papers Fetched", len(raw))
    with col2:
        st.metric("Papers Ranked", len(ranked))
    with col3:
        st.metric("Time Taken", f"{elapsed:.1f}s")

    if errors:
        st.error("Errors during pipeline:")
        for err in errors:
            st.write(f"- {err}")

    filtered = result.get("filtered_papers", [])
    papers_to_index = filtered or ranked
    if papers_to_index:
        vs = VectorStore()
        vs.index_papers(papers_to_index)

    st.page_link(
        "pages/1_Dashboard.py",
        label="→ View in Dashboard",
        use_container_width=True,
    )
