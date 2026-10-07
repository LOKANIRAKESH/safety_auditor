"""Streamlit multi-page dashboard for the Neuro-Symbolic Safety Auditing Framework.

Pages:
  1. Upload & Run    — upload a spec PDF and execute the full 9-phase pipeline
  2. Findings        — filterable, colour-coded finding table with Plotly charts
  3. Knowledge Graph — interactive PyVis equipment graph
  4. PLC Output      — generated IEC 61131-3 Structured Text with download
  5. Audit History   — all past runs from the SQLite store with drill-down
  6. Benchmark       — evaluation metrics and ablation charts from results/

Run: streamlit run ui/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="ICS Safety Auditor",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stMetricValue"] { font-size: 2rem; }
  .finding-high   { color: #ff6b6b; font-weight: bold; }
  .finding-medium { color: #ffa94d; font-weight: bold; }
  .finding-low    { color: #69db7c; font-weight: bold; }
  .stDataFrame thead th { background-color: #1e1e2e !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────
for key, default in [
    ("audit_result", None),
    ("audit_data", {}),
    ("config", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.config is None:
    from src.config import PipelineConfig
    st.session_state.config = PipelineConfig()

# ── DB initialisation (lazy) ───────────────────────────────────────────
@st.cache_resource
def _init_db():
    from db import init_db
    init_db()
    return True

_init_db()

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/ICS-Safety%20Auditor-blue?style=for-the-badge", use_column_width=True)
    st.markdown("### 🔒 Safety Auditor")
    st.caption("Neuro-Symbolic ICS Specification Auditor  \nAmrita Vishwa Vidyapeetham · M.Tech Research")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "📤 Upload & Run",
            "⚠️ Findings",
            "🕸 Knowledge Graph",
            "⚙️ PLC Output",
            "📋 Audit History",
            "📊 Benchmark Metrics",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("**Pipeline Config**")
    model = st.selectbox("LLM Model", ["qwen2.5", "llama3", "qwen2.5:7b", "llama3:8b"])
    st.session_state.config.llm_model = model
    cross_modal = st.toggle("Cross-modal linking", value=True)
    st.session_state.config.enable_cross_modal_linking = cross_modal
    st.caption(f"Invariants: `{st.session_state.config.invariants_dir.name}`")
    st.caption(f"Z3 timeout: `{st.session_state.config.z3_timeout_ms} ms`")


# ═══════════════════════════════════════════════════════════════════════
# PAGE 1 — Upload & Run
# ═══════════════════════════════════════════════════════════════════════
if page == "📤 Upload & Run":
    st.title("📤 Upload Specification & Run Safety Audit")
    st.markdown(
        "Upload an ICS specification PDF (control narrative, C&E table, or P&ID). "
        "The pipeline runs all **9 phases** and stores results in the audit database."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader(
            "Drop specification PDF here",
            type=["pdf"],
            help="Control narrative, cause-effect table, or combined specification document",
        )
        is_real_data = st.checkbox("This is real industrial data (not synthetic benchmark)")

    with col2:
        st.info(
            "**9-Phase Pipeline**\n\n"
            "1. Multimodal ingestion\n"
            "2. LLM entity/rule extraction\n"
            "3. Cross-modal entity linking\n"
            "4. Knowledge graph\n"
            "5. Control rule IR (Pydantic)\n"
            "6. IEC 61511 invariant coverage\n"
            "7. Z3 SMT formal verification\n"
            "8. HTML audit report\n"
            "9. IEC 61131-3 Structured Text"
        )

    if uploaded and st.button("▶ Run Safety Audit", type="primary", use_container_width=True):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / uploaded.name
            pdf_path.write_bytes(uploaded.getvalue())
            output_dir = Path(tmpdir) / "output"

            with st.spinner(f"Running pipeline on **{uploaded.name}**..."):
                try:
                    from src.pipeline.auditor import SafetyAuditor
                    auditor = SafetyAuditor(st.session_state.config)
                    result = auditor.run(pdf_path, output_dir, is_real_data=is_real_data)
                    st.session_state.audit_result = result
                    st.session_state.audit_data = {
                        "report_html": (
                            result.report_path.read_text(encoding="utf-8")
                            if result.report_path and result.report_path.exists() else ""
                        ),
                        "plc_code": (
                            result.plc_output_path.read_text(encoding="utf-8")
                            if result.plc_output_path and result.plc_output_path.exists() else ""
                        ),
                        "findings": [f.to_row() for f in result.findings],
                        "graph_html": (
                            result.graph_html_path.read_text(encoding="utf-8")
                            if result.graph_html_path and result.graph_html_path.exists() else ""
                        ),
                    }
                    st.success(f"Audit complete! Run ID: `{result.run_id}`")
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    st.exception(e)

    r = st.session_state.audit_result
    if r:
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Findings", r.total_findings)
        c2.metric("🔴 HIGH", r.high_count)
        c3.metric("🟠 MEDIUM", r.medium_count)
        c4.metric("🟢 LOW", r.low_count)

        # Severity donut chart
        if r.total_findings:
            fig = go.Figure(go.Pie(
                labels=["HIGH", "MEDIUM", "LOW"],
                values=[r.high_count, r.medium_count, r.low_count],
                hole=0.55,
                marker_colors=["#ff6b6b", "#ffa94d", "#69db7c"],
            ))
            fig.update_layout(
                title="Finding Severity Distribution",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff",
                height=300,
                margin=dict(t=40, b=0, l=0, r=0),
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)

        if st.session_state.audit_data.get("report_html"):
            st.download_button(
                "⬇ Download Full HTML Report",
                st.session_state.audit_data["report_html"],
                file_name="safety_audit_report.html",
                mime="text/html",
            )


# ═══════════════════════════════════════════════════════════════════════
# PAGE 2 — Findings
# ═══════════════════════════════════════════════════════════════════════
elif page == "⚠️ Findings":
    st.title("⚠️ Audit Findings")
    findings = st.session_state.audit_data.get("findings", [])
    if not findings:
        st.info("Run an audit on the **Upload & Run** page first.")
    else:
        df = pd.DataFrame(findings)

        col_f, col_s = st.columns(2)
        with col_f:
            type_opts = df["Type"].unique().tolist() if "Type" in df.columns else []
            type_filter = st.multiselect("Filter by type", type_opts, default=type_opts)
        with col_s:
            sev_filter = st.multiselect(
                "Filter by severity", ["HIGH", "MEDIUM", "LOW"],
                default=["HIGH", "MEDIUM", "LOW"],
            )

        mask = pd.Series([True] * len(df))
        if "Severity" in df.columns:
            mask &= df["Severity"].isin(sev_filter)
        if "Type" in df.columns and type_filter:
            mask &= df["Type"].isin(type_filter)
        filtered = df[mask]

        # Type distribution bar chart
        if not filtered.empty and "Type" in filtered.columns:
            type_counts = filtered["Type"].value_counts().reset_index()
            type_counts.columns = ["Finding Type", "Count"]
            fig = px.bar(
                type_counts, x="Finding Type", y="Count",
                color="Finding Type",
                color_discrete_sequence=px.colors.qualitative.Bold,
                title="Finding Count by Type",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ffffff", height=280, showlegend=False,
                margin=dict(t=40, b=40, l=0, r=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        def _color_sev(val):
            return {
                "HIGH":   "background-color:#3b1c1c; color:#ff6b6b",
                "MEDIUM": "background-color:#3b2e1c; color:#ffa94d",
                "LOW":    "background-color:#1c3b1e; color:#69db7c",
            }.get(val, "")

        if not filtered.empty:
            styled = filtered
            if "Severity" in filtered.columns:
                styled = filtered.style.map(_color_sev, subset=["Severity"])
            st.dataframe(styled, use_container_width=True, height=480)
            st.caption(f"Showing {len(filtered)} of {len(df)} findings")
        else:
            st.success("No findings match the selected filters.")


# ═══════════════════════════════════════════════════════════════════════
# PAGE 3 — Knowledge Graph
# ═══════════════════════════════════════════════════════════════════════
elif page == "🕸 Knowledge Graph":
    st.title("🕸 Equipment Knowledge Graph")
    graph_html = st.session_state.audit_data.get("graph_html", "")
    if not graph_html:
        st.info("Run an audit first to view the knowledge graph.")
    else:
        st.caption(
            "Nodes: equipment (pumps, valves, sensors). "
            "Edges: control rules (condition → action). "
            "Hover for details."
        )
        st.components.v1.html(graph_html, height=680, scrolling=True)

        # Node-type legend from DB if available
        try:
            from db import get_session, AuditRepository
            run_id = st.session_state.audit_result and st.session_state.audit_result.run_id
            if run_id:
                with get_session() as session:
                    repo = AuditRepository(session)
                    nodes = repo.get_kg_nodes(run_id)
                    edges = repo.get_kg_edges(run_id)
                    col_n, col_e = st.columns(2)
                    col_n.metric("Nodes in graph", len(nodes))
                    col_e.metric("Edges (control rules)", len(edges))
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# PAGE 4 — PLC Output
# ═══════════════════════════════════════════════════════════════════════
elif page == "⚙️ PLC Output":
    st.title("⚙️ Generated PLC Structured Text (IEC 61131-3)")
    plc_code = st.session_state.audit_data.get("plc_code", "")
    if not plc_code:
        st.info("Run an audit first.")
    else:
        line_count = plc_code.count("\n")
        st.metric("Lines generated", line_count)
        st.code(plc_code, language="pascal")
        st.download_button(
            "⬇ Download .ST file",
            plc_code,
            file_name="safety_audit_output.st",
            mime="text/plain",
        )
        st.warning(
            "⚠ **Safety notice:** This code is auto-generated from extracted rules. "
            "It MUST be reviewed and validated by a qualified ICS safety engineer "
            "before deployment. Refer to IEC 61131-3 and IEC 61511."
        )


# ═══════════════════════════════════════════════════════════════════════
# PAGE 5 — Audit History
# ═══════════════════════════════════════════════════════════════════════
elif page == "📋 Audit History":
    st.title("📋 Audit History")
    st.caption("All past audit runs persisted in the SQLite store.")

    try:
        from db import get_session, AuditRepository
        with get_session() as session:
            repo = AuditRepository(session)
            runs = repo.get_history(limit=100)
            total_runs = repo.count_runs()
            type_summary = repo.get_finding_type_summary()

        if not runs:
            st.info("No audit runs found. Run an audit on the **Upload & Run** page.")
        else:
            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total runs", total_runs)
            all_high = sum(r.high_count or 0 for r in runs)
            all_med  = sum(r.medium_count or 0 for r in runs)
            all_low  = sum(r.low_count or 0 for r in runs)
            c2.metric("Total HIGH findings", all_high)
            c3.metric("Total MEDIUM findings", all_med)
            c4.metric("Total LOW findings", all_low)

            # Finding type distribution across all runs
            if type_summary:
                ts_df = pd.DataFrame(type_summary)
                fig_ts = px.bar(
                    ts_df, x="type", y="count", color="severity",
                    color_discrete_map={
                        "HIGH": "#ff6b6b", "MEDIUM": "#ffa94d", "LOW": "#69db7c"
                    },
                    barmode="stack",
                    title="All-Time Finding Distribution by Type & Severity",
                )
                fig_ts.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#ffffff", height=300,
                    margin=dict(t=40, b=40, l=0, r=0),
                )
                st.plotly_chart(fig_ts, use_container_width=True)

            st.divider()
            st.subheader("Run History")

            runs_df = pd.DataFrame([r.to_dict() for r in runs])
            runs_df = runs_df.rename(columns={
                "run_id": "Run ID", "input_source": "Input",
                "created_at": "Timestamp", "llm_model": "Model",
                "total_findings": "Findings", "high_count": "HIGH",
                "medium_count": "MED", "low_count": "LOW",
                "cross_modal_linking": "Cross-Modal",
            })
            display_cols = ["Run ID", "Input", "Timestamp", "Model", "Findings", "HIGH", "MED", "LOW"]
            display_cols = [c for c in display_cols if c in runs_df.columns]
            st.dataframe(runs_df[display_cols], use_container_width=True, height=400)

            # Drill-down: select a run to see its findings
            st.divider()
            st.subheader("Drill-down: findings for a specific run")
            run_ids = [r.run_id for r in runs]
            selected_run = st.selectbox("Select run", run_ids)
            if selected_run:
                with get_session() as session2:
                    repo2 = AuditRepository(session2)
                    run_findings = repo2.get_findings(selected_run)
                    kg_nodes = repo2.get_kg_nodes(selected_run)
                    kg_edges = repo2.get_kg_edges(selected_run)

                if run_findings:
                    fd_df = pd.DataFrame([f.to_dict() for f in run_findings])
                    st.dataframe(fd_df, use_container_width=True, height=300)
                else:
                    st.info("No findings stored for this run.")

                kg_col1, kg_col2 = st.columns(2)
                kg_col1.metric("KG Nodes", len(kg_nodes))
                kg_col2.metric("KG Edges", len(kg_edges))

    except Exception as e:
        st.error(f"Could not load audit history: {e}")
        st.exception(e)


# ═══════════════════════════════════════════════════════════════════════
# PAGE 6 — Benchmark Metrics
# ═══════════════════════════════════════════════════════════════════════
elif page == "📊 Benchmark Metrics":
    st.title("📊 Benchmark Evaluation Metrics")
    st.markdown(
        "Results from the **50-package synthetic benchmark** evaluation "
        "(ICS-CERT-aligned injected defects, random seed 42)."
    )

    metrics_path = Path("evaluation/results/main/main/metrics.json")
    if not metrics_path.exists():
        metrics_path = Path(__file__).parent.parent / "evaluation/results/main/main/metrics.json"

    if metrics_path.exists():
        with open(metrics_path) as f:
            m = json.load(f)

        overall = m.get("overall", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precision", f"{overall.get('precision', 0):.3f}")
        c2.metric("Recall",    f"{overall.get('recall', 0):.3f}")
        c3.metric("F1-Score",  f"{overall.get('f1', 0):.3f}")
        c4.metric("Packages",  m.get("package_count", 50))

        st.divider()
        st.subheader("Per-Category Detection Performance")

        per_cat = m.get("per_category", {})
        rows = []
        for cat, vals in per_cat.items():
            rows.append({
                "Defect Category": cat.replace("_", " ").title(),
                "Precision": round(vals.get("precision", 0), 3),
                "Recall":    round(vals.get("recall", 0), 3),
                "F1":        round(vals.get("f1", 0), 3),
                "TP": vals.get("tp", 0),
                "FP": vals.get("fp", 0),
                "FN": vals.get("fn", 0),
            })
        cat_df = pd.DataFrame(rows)

        fig_f1 = px.bar(
            cat_df, x="Defect Category", y="F1",
            color="F1", color_continuous_scale="RdYlGn",
            range_color=[0, 1],
            title="F1-Score per Defect Category",
            text_auto=".3f",
        )
        fig_f1.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff", height=320,
            margin=dict(t=50, b=50, l=0, r=0),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_f1, use_container_width=True)

        # P/R/F1 grouped bar
        melted = cat_df.melt(
            id_vars=["Defect Category"],
            value_vars=["Precision", "Recall", "F1"],
            var_name="Metric", value_name="Score",
        )
        fig_prf = px.bar(
            melted, x="Defect Category", y="Score", color="Metric",
            barmode="group",
            color_discrete_map={"Precision": "#4fc3f7", "Recall": "#81c784", "F1": "#ce93d8"},
            title="Precision / Recall / F1 per Category",
        )
        fig_prf.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff", height=320,
            margin=dict(t=50, b=50, l=0, r=0),
        )
        st.plotly_chart(fig_prf, use_container_width=True)

        st.dataframe(cat_df, use_container_width=True)

    else:
        st.warning(
            "Metrics file not found. Run the evaluation first:\n\n"
            "```\npython run_pipeline.py evaluate --corpus benchmark/corpus\n```"
        )

    # Ablation results
    ablation_path = Path(__file__).parent.parent / "evaluation/results/main/ablation_table.csv"
    if ablation_path.exists():
        st.divider()
        st.subheader("Ablation Study: Cross-Modal Entity Linking")
        ablation_df = pd.read_csv(ablation_path)
        st.dataframe(ablation_df, use_container_width=True)
