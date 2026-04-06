"""
pages/1_pvt.py
==============
PVT page — fluid properties and generated curves.

Tabs
----
Fluid Properties : uncertain_input widgets for all fluid parameters.
PVT Curves       : generates Rs, Bo, Bg, μo vs P and shows table + plots.

No history-match tab: PVT is a forward-only workflow.
"""
import streamlit as st
import plotly.graph_objects as go
import quantia as qu
from quantia import UnitArray, ProbUnitArray, UnitFloat, ProbUnitFloat

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from project.state import Project
from project.io import save_project
from components.uncertain_input import uncertain_input
from components.plots import plot_prob_array

from petro.pvt.models import PVTFluid


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _line_plot(
    x_vals: list[float],
    y_vals: list[float],
    title: str,
    x_label: str,
    y_label: str,
) -> go.Figure:
    """Simple line chart for deterministic (UnitArray) PVT curves."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode="lines",
        line=dict(color="rgb(99, 110, 250)", width=2.5),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        margin=dict(t=60, l=60, r=20, b=50),
    )
    return fig


def _pvt_chart(
    P_array: UnitArray,
    curve,
    title: str,
    y_label: str,
) -> go.Figure:
    """
    Route to plot_prob_array (band) or _line_plot (exact), depending on
    whether curve is ProbUnitArray or UnitArray.
    """
    x_label = f"Pressure [{P_array.unit}]"
    if isinstance(curve, ProbUnitArray):
        return plot_prob_array(
            P_array, curve, title,
            x_label=x_label, y_label=y_label,
        )
    return _line_plot(
        list(P_array.values),
        list(curve.values),
        title, x_label, y_label,
    )


def _p50_list(curve) -> list[float]:
    """Extract P50 values from UnitArray or ProbUnitArray for table display."""
    if isinstance(curve, ProbUnitArray):
        return [curve[i].percentile(50).value for i in range(len(curve))]
    return list(curve.values)


# ─────────────────────────────────────────────────────────────────────────────
# Guard: project must be loaded
# ─────────────────────────────────────────────────────────────────────────────

st.title("PVT")

proj: Project | None = st.session_state.get("project")
if proj is None:
    st.warning("No project loaded. Please create or load a project on the Home page.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab_input, tab_curves = st.tabs(["Fluid Properties", "PVT Curves"])


# ═════════════════════════════════════════════════════════════════════════════
# Tab 1 — Fluid Properties
# ═════════════════════════════════════════════════════════════════════════════

with tab_input:
    st.subheader("Settings")

    fluid_type = st.segmented_control(
        "Fluid type",
        options=["black_oil", "gas_condensate", "gas"],
        selection_mode="single",
        default="black_oil",
        format_func=lambda x: x.replace("_", " ").capitalize(),
        key="pvt_fluid_type",
        width="stretch"
    )
    correlation = st.selectbox(
        "PVT correlation",
        options=["Standing (1947)"],
        key="pvt_correlation",
        help="Additional correlations will be added in future iterations.",
    )
    z_corr = st.selectbox(
        "Z-factor method",
        options=["Hall-Yarborough (1974)", "Papay (1985)"],
        key="pvt_z_corr",
    )

    st.divider()
    st.subheader("Fluid properties")

    gor_sep_i = uncertain_input(
        "Initial GOR",
        ["m3_g_sc/m3_o_sc", "scf/STB"],
        "pvt_GOR_sep_i",
        default_mode="Exact",
        default_value=300.0,
        help="Separator GOR at standard conditions",
    )
    api = uncertain_input(
        "API gravity",
        ["°API"],
        "pvt_api",
        default_mode="Exact",
        default_value=35.0,
        help="Oil API gravity",
    )
    SG_g = uncertain_input(
        "Gas specific gravity",
        ["1"],
        "pvt_SGg",
        default_mode="Exact",
        default_value=0.65,
        help="Gas SG relative to air (typical range 0.55-0.85)",
    )
    T_res = uncertain_input(
        "Reservoir temperature",
        ["°C", "°F", "K", "°R"],
        "pvt_Tres",
        default_mode="Exact",
        default_value=100.0,
        help="Static reservoir temperature",
    )
    P_sep = uncertain_input(
        "Separator pressure",
        ["psia", "psig", "bara", "barg", "kg/cm2", "Pa"],
        "pvt_Psep",
        default_mode="Exact",
        default_value=50.0,
        help="Separator pressure for GOR correction",
    )
    T_sep = uncertain_input(
        "Separator temperature",
        ["°C", "°F", "K", "°R"],
        "pvt_Tsep",
        default_mode="Exact",
        default_value=20.0,
        help="Separator temperature for GOR correction",
    )

    # Build fluid from current inputs
    _corr_key = "standing"
    _z_key    = "hall_yarborough" if "Hall" in z_corr else "papay"

    fluid = PVTFluid(
        fluid_type   = fluid_type,
        gor_sep_i    = gor_sep_i,
        api          = api,
        SG_g         = SG_g,
        T_res        = T_res,
        P_sep        = P_sep,
        T_sep        = T_sep,
        correlation  = _corr_key,
        z_correlation= _z_key,
    )

    # Persist current fluid to session (not project — user must click Save)
    st.session_state["pvt_fluid"] = fluid

    st.divider()

    if st.button("Save fluid properties to project", type="primary", key="pvt_save"):
        proj.pvt = fluid.to_dict()
        st.session_state.project = proj
        st.success("Fluid properties saved to project.")


# ═════════════════════════════════════════════════════════════════════════════
# Tab 2 — PVT Curves
# ═════════════════════════════════════════════════════════════════════════════

with tab_curves:
    fluid: PVTFluid | None = st.session_state.get("pvt_fluid")

    if fluid is None:
        st.info("Enter fluid properties in the Fluid Properties tab first.")
        st.stop()

    col_left, col_right = st.columns(2)

    with col_right:
        st.subheader("Display units")

    with col_left:
        st.subheader("Pressure range")

        cc1, cc2, cc3 = st.columns(3)
        P_min_val = cc1.number_input(
            "Min pressure [bara]",
            value=10.0,
            min_value=1.0,
            max_value=2000.0,
            step=10.0,
            key="pvt_Pmin",
        )
        P_max_val = cc2.number_input(
            "Max pressure [bara]",
            value=100.0,
            min_value=1.0,
            max_value=2000.0,
            step=10.0,
            key="pvt_Pmax",
        )
        n_pts = cc3.slider("Number of points", min_value=5, max_value=50, value=20, key="pvt_npts")

        if P_min_val >= P_max_val:
            st.error("Min pressure must be less than Max pressure.")
            st.stop()

    if st.button("Generate PVT table", type="primary", key="pvt_generate"):

        with st.spinner("Computing PVT curves…"):
            P_step  = (P_max_val - P_min_val) / (n_pts - 1)
            P_vals  = [P_min_val + i * P_step for i in range(n_pts)]
            P_array = qu.QA(P_vals, "bara")

            with qu.config(n_samples=proj.n_samples, seed=proj.seed):
                Pb     = fluid._Pb
                Rs_c   = fluid.Rs_curve(P_array)
                Bo_c   = fluid.Bo_curve(P_array)
                Bg_c   = fluid.Bg_curve(P_array)
                mu_o_c = fluid.mu_o_curve(P_array)
                mu_g_c = fluid.mu_g_curve(P_array)
                c_o_c  = fluid.c_o_curve(P_array)
                # rho_o_c = fluid.rho_o_curve(P_array)

        # ── Plots ────────────────────────────────────────────────────────────
        st.divider()
        st.subheader("PVT Curves")

        is_prob = isinstance(Rs_c, ProbUnitArray)
        if is_prob:
            st.caption(
                f"Showing P10/P50/P90 bands "
                f"(n = {proj.n_samples:,} MC samples)"
            )
            st.markdown(
                f"Bubblepoint pressure:\n\n"
                f"P10: {Pb.to("bara").percentile(10):.2f}\n\n"
                f"P50: {Pb.to("bara").percentile(50):.2f}\n\n"
                f"P90: {Pb.to("bara").percentile(90):.2f}"
            )
        else:
            st.markdown(f"Bubblepoint pressure:: {Pb.to("bara"):.2f}\n\n")

        col_a, col_b = st.columns(2)
        col_c, col_d = st.columns(2)
        col_e, col_f = st.columns(2)

        with col_a:
            st.plotly_chart(
                _pvt_chart(P_array, Rs_c, "Solution GOR", f"Rs [{Rs_c._unit if is_prob else Rs_c.unit}]"),
                use_container_width=True,
            )
        with col_b:
            st.plotly_chart(
                _pvt_chart(P_array, c_o_c.to("1/psia"), "Oil Compressibility", f"co [{c_o_c._unit if is_prob else c_o_c.unit}]"),
                use_container_width=True,
            )
        with col_c:
            st.plotly_chart(
                _pvt_chart(P_array, Bo_c, "Oil FVF", f"Bo [{Bo_c._unit if is_prob else Bo_c.unit}]"),
                use_container_width=True,
            )
        with col_d:
            st.plotly_chart(
                _pvt_chart(P_array, Bg_c, "Gas FVF", f"Bg [{Bg_c._unit if is_prob else Bg_c.unit}]"),
                use_container_width=True,
            )
        with col_e:
            st.plotly_chart(
                _pvt_chart(P_array, mu_o_c, "Oil Viscosity", f"μo [{mu_o_c._unit if is_prob else mu_o_c.unit}]"),
                use_container_width=True,
            )
        with col_f:
            st.plotly_chart(
                _pvt_chart(P_array, mu_g_c, "Gas Viscosity", f"μg [{mu_g_c._unit if is_prob else mu_g_c.unit}]"),
                use_container_width=True,
            )

        # ── Table ─────────────────────────────────────────────────────────────
        st.divider()
        st.subheader("PVT Table" + (" — P50 values" if is_prob else ""))

        import pandas as pd
        df = pd.DataFrame({
            "P  [bara]":  [round(v, 1) for v in P_vals],
            "Rs [m3/m3]": [round(v, 1) for v in _p50_list(Rs_c)],
            "Bo [m3/m3]": [round(v, 4) for v in _p50_list(Bo_c)],
            "Bg [m3/m3]": [f"{v:.6f}"  for v in _p50_list(Bg_c)],
            "μo [cP]":    [round(v, 4) for v in _p50_list(mu_o_c)],
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── CSV download ──────────────────────────────────────────────────────
        st.download_button(
            "Download PVT table (CSV)",
            data=df.to_csv(index=False),
            file_name="pvt_table.csv",
            mime="text/csv",
        )