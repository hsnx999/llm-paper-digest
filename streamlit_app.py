import streamlit as st
from datetime import datetime
from core.database import Database
from core.config import Config

st.set_page_config(
    page_title="LLM Paper Digest",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .main-title {
        color: #e8e8e8;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .main-subtitle {
        color: #9b9b9b;
        font-size: 1.2rem;
        font-weight: 400;
        margin-top: 0;
        padding-top: 0;
    }
    .stat-card {
        background-color: #1a1d2e;
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .stat-number {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
    }
    .stat-label {
        color: #9b9b9b;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .nav-hint {
        color: #6b6b6b;
        text-align: center;
        margin-top: 3rem;
        font-size: 1rem;
    }
    .footer {
        color: #555555;
        text-align: center;
        margin-top: 4rem;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

db = Database()
config = Config()

last_run = db.get_last_run()
total_runs = len(db.get_all_runs())
total_papers = db.get_total_papers()

st.markdown('<p class="main-title">LLM Paper Digest</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="main-subtitle">Automated weekly ArXiv AI paper intelligence</p>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f'<div class="stat-card">'
        f'<div class="stat-number">{total_runs}</div>'
        f'<div class="stat-label">Total Runs</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="stat-card">'
        f'<div class="stat-number">{total_papers}</div>'
        f'<div class="stat-label">Papers Digested</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with col3:
    last_run_time = "Never"
    if last_run and last_run.finished_at:
        last_run_time = last_run.finished_at.strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f'<div class="stat-card">'
        f'<div class="stat-number">{last_run_time}</div>'
        f'<div class="stat-label">Last Run</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<p class="nav-hint">Navigate to pages using the sidebar →</p>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="footer">Built with LangGraph · LangChain · Streamlit</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### System Info")
    st.markdown(f"**Provider:** {config.LLM_PROVIDER}")
    st.markdown(f"**Model:** {config.model_name}")
    st.markdown("---")
    if last_run:
        st.markdown(f"**Last Run:** {last_run.started_at.strftime('%Y-%m-%d %H:%M')}")
        st.markdown(f"**Status:** {last_run.status}")
    else:
        st.markdown("**Last Run:** Never")
    st.markdown("---")
    st.markdown(f"**Total Papers:** {total_papers}")
