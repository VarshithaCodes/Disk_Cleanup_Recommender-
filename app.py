"""
Disk Cleanup Recommender — Streamlit App

Agent Loop:
1. Scan disk
2. Extract metadata
3. Call LLM (Gemini) to classify each file
4. Validate classification (rule-based safety layer)
5. Ask human approval (Approve/Reject buttons in UI)
6. Execute delete tool (move to recycle folder)
7. Generate report (CSV + Markdown)
"""

import os
import streamlit as st

from src.scanner import scan_directory
from src.classifier import classify_file
from src.deleter import move_to_recycle
from src.report_generator import generate_csv_report, generate_markdown_report

st.set_page_config(page_title="Disk Cleanup Recommender", layout="wide")

st.title("🧹 Disk Cleanup Recommender")
st.caption("AI-assisted disk cleanup with a human approval gate. Files are never permanently "
           "deleted — approved files are moved to a local `deleted/` recycle folder.")

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "files" not in st.session_state:
    st.session_state.files = []
if "classified" not in st.session_state:
    st.session_state.classified = []
if "decisions" not in st.session_state:
    st.session_state.decisions = {}  # path -> "approve" | "reject"
if "report_results" not in st.session_state:
    st.session_state.report_results = []

# ---------------------------------------------------------------------------
# Step 1: Scan
# ---------------------------------------------------------------------------
st.header("1. Scan Folder")

default_path = "data/sample_disk"
folder = st.text_input("Folder Path", value=default_path)

col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 Scan Folder", use_container_width=True):
        try:
            st.session_state.files = scan_directory(folder)
            st.session_state.classified = []
            st.session_state.decisions = {}
            st.session_state.report_results = []
            st.success(f"Scanned {len(st.session_state.files)} files.")
        except ValueError as e:
            st.error(str(e))

if st.session_state.files:
    st.dataframe(st.session_state.files, use_container_width=True)

# ---------------------------------------------------------------------------
# Step 2: AI Classification
# ---------------------------------------------------------------------------
st.header("2. AI Analysis")

with col2:
    if st.button("🤖 Run AI Analysis", use_container_width=True, disabled=not st.session_state.files):
        with st.spinner("Classifying files..."):
            classified = []
            for f in st.session_state.files:
                result = classify_file(f)
                classified.append({**f, **result})
            st.session_state.classified = classified
        st.success("Classification complete.")

if not os.environ.get("GEMINI_API_KEY"):
    st.info("No `GEMINI_API_KEY` found in environment — using offline heuristic classifier "
            "for demo purposes. Set the env var to use Gemini live.")

# ---------------------------------------------------------------------------
# Step 3: Human Approval Gate
# ---------------------------------------------------------------------------
if st.session_state.classified:
    st.header("3. Review & Approve")
    st.write("Files classified as **SAFE_DELETE** require your approval before being moved "
             "to the recycle folder. **REVIEW** files are shown for awareness but require "
             "manual handling. **KEEP** files are listed for transparency only.")

    for item in st.session_state.classified:
        path = item["path"]
        classification = item["classification"]

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1, 2])
            cols[0].markdown(f"**{path}**\n\n_{item['reason']}_")
            cols[1].metric("Size (MB)", item["size_mb"])
            cols[2].metric("Age (days)", item["age_days"])

            badge_color = {
                "SAFE_DELETE": "🔴",
                "REVIEW": "🟡",
                "KEEP": "🟢",
            }.get(classification, "⚪")
            cols[3].markdown(f"### {badge_color} {classification}")

            if classification == "SAFE_DELETE":
                decision = st.session_state.decisions.get(path)
                btn_col = cols[4]
                approve_clicked = btn_col.button("✅ Approve", key=f"approve_{path}")
                reject_clicked = btn_col.button("❌ Reject", key=f"reject_{path}")

                if approve_clicked:
                    st.session_state.decisions[path] = "approve"
                if reject_clicked:
                    st.session_state.decisions[path] = "reject"

                if path in st.session_state.decisions:
                    cols[4].caption(f"Decision: **{st.session_state.decisions[path]}**")
            else:
                cols[4].caption("No action needed")

# ---------------------------------------------------------------------------
# Step 4: Execute & Report
# ---------------------------------------------------------------------------
if st.session_state.classified:
    st.header("4. Execute Cleanup & Generate Report")

    safe_delete_items = [c for c in st.session_state.classified if c["classification"] == "SAFE_DELETE"]
    pending = [c for c in safe_delete_items if c["path"] not in st.session_state.decisions]

    if pending:
        st.warning(f"{len(pending)} SAFE_DELETE file(s) still need a decision before running cleanup.")

    if st.button("🚀 Run Cleanup", type="primary", disabled=bool(pending)):
        results = []
        for item in st.session_state.classified:
            row = {
                "path": item["path"],
                "size_mb": item["size_mb"],
                "age_days": item["age_days"],
                "classification": item["classification"],
                "reason": item["reason"],
                "action": "NONE",
                "moved_to": "",
            }

            if item["classification"] == "SAFE_DELETE":
                decision = st.session_state.decisions.get(item["path"])
                if decision == "approve":
                    new_path = move_to_recycle(item["path"], "deleted", source_root=folder)
                    row["action"] = "MOVED_TO_RECYCLE"
                    row["moved_to"] = new_path
                else:
                    row["action"] = "KEPT_BY_USER"

            results.append(row)

        st.session_state.report_results = results

        csv_path = generate_csv_report(results, "outputs/cleanup_report.csv")
        md_path = generate_markdown_report(results, "outputs/cleanup_report.md")

        st.success("Cleanup complete! Reports generated.")
        st.session_state.csv_path = csv_path
        st.session_state.md_path = md_path

# ---------------------------------------------------------------------------
# Step 5: Show Report
# ---------------------------------------------------------------------------
if st.session_state.report_results:
    st.header("5. Cleanup Report")

    moved = [r for r in st.session_state.report_results if r["action"] == "MOVED_TO_RECYCLE"]
    recovered = sum(r["size_mb"] for r in moved)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Files Scanned", len(st.session_state.report_results))
    m2.metric("Files Moved to Recycle", len(moved))
    m3.metric("Recovered Space (MB)", round(recovered, 2))

    st.dataframe(st.session_state.report_results, use_container_width=True)

    dl_col1, dl_col2 = st.columns(2)
    if os.path.exists("outputs/cleanup_report.csv"):
        with open("outputs/cleanup_report.csv", "rb") as f:
            dl_col1.download_button("⬇️ Download CSV Report", f, file_name="cleanup_report.csv")
    if os.path.exists("outputs/cleanup_report.md"):
        with open("outputs/cleanup_report.md", "rb") as f:
            dl_col2.download_button("⬇️ Download Markdown Report", f, file_name="cleanup_report.md")

    st.info("Files were moved to the local `deleted/` folder, not permanently removed. "
            "You can restore them manually if needed.")
