"""
app.py
======
petro-app entry point and home page.

Run with:
    streamlit run app.py
"""
import json
import streamlit as st

from project.state import Project
from project.io import save_project, load_project


# ── Session state bootstrap ───────────────────────────────────────────────────

def _init_session():
    defaults = {
        "project":          None,
        "project_n_samples": 3000,
        "project_seed":     42,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Page ──────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="petro-app",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

_init_session()

st.title("🛢️ petro-app")
st.caption("Reservoir & production engineering — single well or single field")

tab_new, tab_load = st.tabs(["New project", "Load project"])

# ── New project ───────────────────────────────────────────────────────────────
with tab_new:
    st.subheader("Start a new project")

    c1, c2 = st.columns(2)
    with c1:
        p_name  = st.text_input("Project name", value="Well X — Evaluation")
        p_scope = st.selectbox("Scope", ["well", "field"],
                               help="well: single-well analysis | field: material balance")
        p_units = st.selectbox("Unit system", ["field", "si"],
                               help="Field: psia, bbl, ft, °F | SI: Pa, m³, m, °C")
    with c2:
        p_n = st.number_input(
            "Monte Carlo samples", value=3000, min_value=100, max_value=50_000, step=500,
            help="More samples → smoother distributions, slower calculations",
        )
        p_seed = st.number_input(
            "Random seed", value=42, min_value=0,
            help="Fix for reproducibility; change to explore natural variability",
        )

    if st.button("Create project", type="primary"):
        proj = Project(
            name=p_name, scope=p_scope, units=p_units,
            n_samples=int(p_n), seed=int(p_seed),
        )
        st.session_state.project          = proj
        st.session_state.project_n_samples = int(p_n)
        st.session_state.project_seed     = int(p_seed)
        st.success(f"Project **{p_name}** created. Navigate to PVT in the sidebar.")

# ── Load project ──────────────────────────────────────────────────────────────
with tab_load:
    st.subheader("Load an existing project")

    uploaded = st.file_uploader("Choose a .json project file", type=["json"])
    if uploaded is not None:
        try:
            data = json.loads(uploaded.read().decode("utf-8"))
            proj = Project.from_dict(data)
            st.session_state.project          = proj
            st.session_state.project_n_samples = proj.n_samples
            st.session_state.project_seed     = proj.seed
            st.success(f"Loaded: **{proj.name}**")
        except Exception as exc:
            st.error(f"Could not load project: {exc}")

# ── Active project status ─────────────────────────────────────────────────────
st.divider()
st.subheader("Active project")

proj: Project | None = st.session_state.project

if proj is None:
    st.info("No project loaded. Create or load one above to unlock the sidebar pages.")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Name",       proj.name)
    c2.metric("Scope",      proj.scope.title())
    c3.metric("MC samples", f"{proj.n_samples:,}")
    c4.metric("Created",    proj.created)

    st.subheader("Module status")
    cols = st.columns(6)
    modules = ["pvt", "volumetrics", "material_balance", "dca", "ipr", "rta"]
    labels  = ["PVT", "Volumetrics", "Mat. Balance", "DCA", "IPR", "RTA"]
    for col, mod, lbl in zip(cols, modules, labels):
        done = bool(getattr(proj, mod))
        col.metric(lbl, "✅" if done else "⬜")

    # Download button
    st.subheader("Save project")
    st.download_button(
        label="📥 Download project JSON",
        data=json.dumps(proj.to_dict(), indent=2),
        file_name=f"{proj.name.replace(' ', '_')}.json",
        mime="application/json",
    )