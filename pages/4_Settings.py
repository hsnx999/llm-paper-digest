import streamlit as st
from core.config import Config
from core.database import Database

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .settings-header { color: #e8e8e8; font-size: 1.8rem; font-weight: 600; }
    .section-title { color: #9b9b9b; font-size: 1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<p class="settings-header">⚙ Settings</p>',
    unsafe_allow_html=True,
)

config = Config()

st.markdown('<p class="section-title">Edit Configuration</p>', unsafe_allow_html=True)

with st.form("settings_form"):
    st.text_input("LLM Provider", value="groq", disabled=True)

    groq_key = st.text_input(
        "Groq API Key",
        value=config.GROQ_API_KEY or "",
        type="password",
        placeholder="gsk_...",
    )

    default_topics = st.text_input(
        "Default Topics (comma-separated)",
        value=config.DEFAULT_TOPICS,
    )

    default_categories = st.text_input(
        "Default Categories (comma-separated)",
        value=config.DEFAULT_CATEGORIES,
    )

    col1, col2 = st.columns(2)
    with col1:
        top_n = st.number_input(
            "Top N Papers",
            min_value=1,
            max_value=50,
            value=config.TOP_N_PAPERS,
        )
    with col2:
        days_lookback = st.number_input(
            "Days Lookback",
            min_value=1,
            max_value=60,
            value=config.DAYS_LOOKBACK,
        )

    col3, col4 = st.columns(2)
    with col3:
        papers_per_run = st.number_input(
            "Papers Per Run",
            min_value=10,
            max_value=200,
            value=config.PAPERS_PER_RUN,
        )
    with col4:
        log_level_options = ["DEBUG", "INFO", "WARNING", "ERROR"]
        default_log_idx = log_level_options.index(config.LOG_LEVEL) if config.LOG_LEVEL in log_level_options else 1
        log_level = st.selectbox(
            "Log Level",
            options=log_level_options,
            index=default_log_idx,
        )

    saved = st.form_submit_button("💾 Save Settings", use_container_width=True, type="primary")

if saved:
    from dotenv import set_key
    pairs = {
        "GROQ_API_KEY": groq_key,
        "DEFAULT_TOPICS": default_topics,
        "DEFAULT_CATEGORIES": default_categories,
        "TOP_N_PAPERS": str(top_n),
        "DAYS_LOOKBACK": str(days_lookback),
        "PAPERS_PER_RUN": str(papers_per_run),
        "LOG_LEVEL": log_level,
    }
    for key, value in pairs.items():
        set_key(".env", key, value)
    st.success("Settings saved!")
    st.rerun()

st.markdown("---")
st.markdown('<p class="section-title">Current Effective Configuration</p>', unsafe_allow_html=True)

cfg = Config()
st.json({
    "MODEL_NAME": cfg.model_name,
    "DEFAULT_TOPICS": cfg.DEFAULT_TOPICS,
    "DEFAULT_CATEGORIES": cfg.DEFAULT_CATEGORIES,
    "TOP_N_PAPERS": cfg.TOP_N_PAPERS,
    "DAYS_LOOKBACK": cfg.DAYS_LOOKBACK,
    "OUTPUT_DIR": cfg.OUTPUT_DIR,
    "DATA_DIR": cfg.DATA_DIR,
})
