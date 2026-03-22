"""
components/uncertain_input.py
==============================
Universal uncertain input widget.

Every single-value input in petro-app uses uncertain_input().
Returns UnitFloat for Exact mode, ProbUnitFloat for all distribution
modes. The output type drives every downstream calculation automatically
via petro's dispatch utilities.

Seed stability
--------------
Each input gets a deterministic seed derived from the project seed and
the widget key. This means:
  - Same project seed + same inputs → same samples on every re-render.
  - Different keys → different sample sequences (no accidental correlation).
"""
from __future__ import annotations
import streamlit as st
import quantia as qu
from quantia import UnitFloat, ProbUnitFloat


def _key_seed(base_seed: int | None, key: str) -> int | None:
    """Derive a stable per-input seed from the project seed and the key string."""
    if base_seed is None:
        return None
    # Simple deterministic mixing — not cryptographic, just stable
    key_int = sum(ord(c) * (i + 1) for i, c in enumerate(key)) % 99_991
    return (base_seed * 31_337 + key_int) % (2 ** 31)


def uncertain_input(
    label:         str,
    unit:          str,
    key:           str,
    distributions: list[str] | None = None,
    default_mode:  str = "Exact",
    help:          str | None = None,
    default_value: float = 0.0,
) -> UnitFloat | ProbUnitFloat:
    """
    Render a labeled input with a distribution selector.

    Parameters
    ----------
    label         : displayed above the widget
    unit          : quantia unit string shown in brackets, e.g. "psia"
    key           : unique Streamlit key — prefix with page name to
                    avoid collisions, e.g. "pvt_api", "vol_porosity"
    distributions : available modes; default is all four
    default_mode  : which mode is pre-selected
    help          : optional tooltip
    default_value : starting value for Exact mode

    Returns
    -------
    UnitFloat  when mode == "Exact"
    ProbUnitFloat otherwise (n_samples from project session state)
    """
    if distributions is None:
        distributions = ["Exact", "Uniform", "Normal", "Triangular"]

    n_samples  = st.session_state.get("project_n_samples", 3000)
    base_seed  = st.session_state.get("project_seed", None)
    this_seed  = _key_seed(base_seed, key)

    st.markdown(
        f"**{label}** &nbsp;`[{unit}]`"
        + (f"<br><small>{help}</small>" if help else ""),
        unsafe_allow_html=True,
    )

    mode = st.selectbox(
        "Distribution",
        options=distributions,
        index=distributions.index(default_mode) if default_mode in distributions else 0,
        key=f"{key}_mode",
        label_visibility="collapsed",
    )

    # ── Exact ─────────────────────────────────────────────────────────────────
    if mode == "Exact":
        val = st.number_input(
            "Value", value=float(default_value),
            key=f"{key}_val", label_visibility="collapsed",
        )
        return qu.Q(val, unit)

    # ── Uniform ───────────────────────────────────────────────────────────────
    elif mode == "Uniform":
        c1, c2 = st.columns(2)
        lo = c1.number_input("Low",  value=float(default_value) * 0.8 or 0.0,
                              key=f"{key}_lo")
        hi = c2.number_input("High", value=float(default_value) * 1.2 or 1.0,
                              key=f"{key}_hi")
        if lo >= hi:
            st.error("Low must be less than High.")
            return qu.Q(lo, unit)
        with qu.config(n_samples=n_samples, seed=this_seed):
            return qu.ProbUnitFloat.uniform(lo, hi, unit, n=n_samples)

    # ── Normal ────────────────────────────────────────────────────────────────
    elif mode == "Normal":
        c1, c2 = st.columns(2)
        mean = c1.number_input("Mean",    value=float(default_value),
                               key=f"{key}_mean")
        std  = c2.number_input("Std dev", value=abs(float(default_value)) * 0.1 or 1.0,
                               min_value=1e-9, key=f"{key}_std")
        with qu.config(n_samples=n_samples, seed=this_seed):
            return qu.ProbUnitFloat.normal(mean, std, unit, n=n_samples)

    # ── Triangular ────────────────────────────────────────────────────────────
    elif mode == "Triangular":
        c1, c2, c3 = st.columns(3)
        lo   = c1.number_input("Low",  value=float(default_value) * 0.8 or 0.0,
                               key=f"{key}_lo")
        mode_v = c2.number_input("Mode", value=float(default_value),
                                 key=f"{key}_mode_val")
        hi   = c3.number_input("High", value=float(default_value) * 1.2 or 1.0,
                               key=f"{key}_hi")
        if not (lo <= mode_v <= hi):
            st.error("Must satisfy Low ≤ Mode ≤ High.")
            return qu.Q(mode_v, unit)
        if lo == hi:
            st.error("Low and High must differ.")
            return qu.Q(lo, unit)
        with qu.config(n_samples=n_samples, seed=this_seed):
            return qu.ProbUnitFloat.triangular(lo, mode_v, hi, unit, n=n_samples)

    else:
        st.error(f"Unknown mode: {mode}")
        return qu.Q(float(default_value), unit)