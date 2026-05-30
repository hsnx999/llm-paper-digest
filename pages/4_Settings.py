import os
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

    saved = st.form_submit_button("💾 Save Settings", use_container_width=True, type="primary")

if saved:
    lines = []
    if os.path.exists(".env"):
        with open(".env") as f:
            existing = f.read()
        seen = set()
        for line in existing.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                lines.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            seen.add(key)
        for key in seen:
            lines = [l for l in lines if not l.startswith(key + "=")]
    else:
        seen = set()

    pairs = {
        "GROQ_API_KEY": groq_key,
        "DEFAULT_TOPICS": default_topics,
        "DEFAULT_CATEGORIES": default_categories,
        "TOP_N_PAPERS": str(top_n),
        "DAYS_LOOKBACK": str(days_lookback),
    }

    for key, value in pairs.items():
        if key not in seen:
            lines.append(f"{key}={value}")
        else:
            lines.append(f"{key}={value}")

    with open(".env", "w") as f:
        f.write("\n".join(lines) + "\n")

    st.success("Settings saved! Restart the app for changes to take full effect.")
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
