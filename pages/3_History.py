import json
import os
import streamlit as st
from core.database import Database
from core.config import Config

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .history-header { color: #e8e8e8; font-size: 1.8rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

db = Database()
config = Config()

st.markdown(
    '<p class="history-header">📜 Run History</p>',
    unsafe_allow_html=True,
)

runs = db.get_all_runs()

if not runs:
    st.info("No pipeline runs found. Run the pipeline from the Run Pipeline page.")
    st.stop()

data = []
for r in runs:
    started = r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else ""
    finished = r.finished_at.strftime("%Y-%m-%d %H:%M:%S") if r.finished_at else ""
    status_emoji = {"success": "✅", "failed": "❌", "running": "🔄"}.get(r.status, "❓")
    data.append({
        "Run ID": r.run_id[:8] + "...",
        "Started": started,
        "Finished": finished,
        "Status": f"{status_emoji} {r.status}",
        "Papers": r.paper_count,
        "Top N": r.top_n,
        "_run_id": r.run_id,
        "_json_path": r.json_path,
        "_md_path": r.md_path,
    })

st.dataframe(
    data,
    column_order=["Run ID", "Started", "Finished", "Status", "Papers", "Top N"],
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

for r in runs:
    with st.expander(f"Run {r.run_id[:8]} — {r.started_at.strftime('%Y-%m-%d %H:%M')}", expanded=False):
        st.json({
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "paper_count": r.paper_count,
            "top_n": r.top_n,
            "topics": r.topics,
            "categories": r.categories,
            "json_path": r.json_path,
            "md_path": r.md_path,
        })

        col1, col2, col3 = st.columns(3)

        with col1:
            if r.json_path and os.path.exists(r.json_path):
                with open(r.json_path) as f:
                    json_content = f.read()
                st.download_button(
                    "📥 View JSON",
                    data=json_content,
                    file_name=os.path.basename(r.json_path),
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.button("📥 View JSON", disabled=True, use_container_width=True)

        with col2:
            if r.md_path and os.path.exists(r.md_path):
                with open(r.md_path) as f:
                    md_content = f.read()
                st.download_button(
                    "📥 View MD",
                    data=md_content,
                    file_name=os.path.basename(r.md_path),
                    mime="text/markdown",
                    use_container_width=True,
                )
            else:
                st.button("📥 View MD", disabled=True, use_container_width=True)

        with col3:
            with st.popover(f"🗑 Delete", use_container_width=True):
                st.warning(f"Delete run {r.run_id[:8]}?")
                if st.button("Yes, delete", key=f"confirm_del_{r.run_id}", use_container_width=True):
                    if r.json_path and os.path.exists(r.json_path):
                        os.remove(r.json_path)
                    if r.md_path and os.path.exists(r.md_path):
                        os.remove(r.md_path)
                    db.delete_run(r.run_id)
                    st.success(f"Run {r.run_id[:8]} deleted")
                    st.rerun()
