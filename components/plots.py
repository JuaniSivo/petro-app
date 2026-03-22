"""
components/plots.py
===================
Standard plots for petro-app.

Three functions cover every chart in the app:
    plot_prob_array      — uncertainty band (PVT curves, forecasts, IPR)
    plot_histogram       — distribution with P10/P50/P90 (OOIP, EUR)
    plot_retrospective   — parameter evolution over time (DCA, MB)

Visual language is fixed so every page looks identical:
    P50  → solid #636EFA line
    band → #636EFA at 20% opacity
    P10 markers → #EF553B dashed
    P90 markers → #00CC96 dashed
    observed    → dark scatter circles
"""
from __future__ import annotations
import plotly.graph_objects as go
from quantia import UnitArray, ProbUnitArray, ProbUnitFloat, UnitFloat

# ── Palette ───────────────────────────────────────────────────────────────────
_BAND_FILL  = "rgba(99, 110, 250, 0.18)"
_P50_LINE   = "rgb(99, 110, 250)"
_P10_LINE   = "rgb(239, 85, 59)"
_P90_LINE   = "rgb(0, 204, 150)"
_OBS_MARKER = "rgb(30, 30, 30)"
_HIST_BAR   = "rgba(99, 110, 250, 0.70)"


def plot_prob_array(
    x:          UnitArray,
    y:          ProbUnitArray,
    title:      str,
    x_label:    str | None = None,
    y_label:    str | None = None,
    confidence: float = 0.80,
    history_x:  UnitArray | None = None,
    history_y:  UnitArray | None = None,
) -> go.Figure:
    """
    Uncertainty band plot — the workhorse of petro-app.

    Draws P50 as a solid line and a symmetric confidence band (default
    P10–P90). Optionally overlays observed data as open-circle scatter.

    Parameters
    ----------
    x           : X-axis values (e.g. pressure array)
    y           : ProbUnitArray — one ProbUnitFloat per x point
    confidence  : width of the band, e.g. 0.80 → P10–P90
    history_x/y : optional observed data to overlay
    """
    x_vals = list(x.values)
    tail   = (1.0 - confidence) / 2.0
    plo    = int(round(tail * 100))
    phi    = int(round((1.0 - tail) * 100))

    p50 = [y[i].percentile(50).value  for i in range(len(y))]
    plo_vals = [y[i].percentile(plo).value for i in range(len(y))]
    phi_vals = [y[i].percentile(phi).value for i in range(len(y))]

    fig = go.Figure()

    # Band (filled polygon)
    fig.add_trace(go.Scatter(
        x=x_vals + x_vals[::-1],
        y=phi_vals + plo_vals[::-1],
        fill="toself",
        fillcolor=_BAND_FILL,
        line=dict(color="rgba(0,0,0,0)"),
        name=f"P{plo}–P{phi}",
        hoverinfo="skip",
    ))

    # P50 line
    fig.add_trace(go.Scatter(
        x=x_vals, y=p50,
        mode="lines",
        line=dict(color=_P50_LINE, width=2.5),
        name="P50",
    ))

    # Observed data
    if history_x is not None and history_y is not None:
        fig.add_trace(go.Scatter(
            x=list(history_x.values),
            y=list(history_y.values),
            mode="markers",
            marker=dict(color=_OBS_MARKER, size=7, symbol="circle-open", line=dict(width=1.5)),
            name="Observed",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title=x_label or str(x.unit),
        yaxis_title=y_label or str(y._unit),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, l=60, r=20, b=50),
    )
    return fig


def plot_histogram(
    x:                ProbUnitFloat,
    title:            str,
    label:            str | None = None,
    show_percentiles: bool = True,
    bins:             int = 30,
) -> go.Figure:
    """
    Distribution histogram with optional P10/P50/P90 vertical lines.

    Used for any single uncertain result: OOIP, EUR, N, k, etc.
    """
    samples  = list(x._samples)
    unit_str = str(x._unit)
    p10 = x.percentile(10).value
    p50 = x.percentile(50).value
    p90 = x.percentile(90).value

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=samples, nbinsx=bins,
        name=label or title,
        marker_color=_HIST_BAR,
        hovertemplate=f"%{{x:.4g}} {unit_str}<br>Count: %{{y}}<extra></extra>",
    ))

    if show_percentiles:
        for val, name, color in [
            (p10, f"P10  {p10:.4g}", _P10_LINE),
            (p50, f"P50  {p50:.4g}", _P50_LINE),
            (p90, f"P90  {p90:.4g}", _P90_LINE),
        ]:
            fig.add_vline(
                x=val,
                line=dict(color=color, width=1.5, dash="dash"),
                annotation=dict(text=name, font=dict(size=11, color=color)),
                annotation_position="top right",
            )

    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title=label or unit_str,
        yaxis_title="Count",
        template="plotly_white",
        bargap=0.04,
        margin=dict(t=60, l=60, r=20, b=50),
    )
    return fig


def plot_retrospective(
    snapshot_times: UnitArray,
    p10_values:     UnitArray,
    p50_values:     UnitArray,
    p90_values:     UnitArray,
    title:          str,
    y_label:        str,
) -> go.Figure:
    """
    Parameter estimate evolution as more data arrives.

    Shows a funnel: wide P10–P90 band early on, narrowing as the model
    accumulates evidence. Used for EUR (DCA), N (material balance), etc.
    """
    t   = list(snapshot_times.values)
    p10 = list(p10_values.values)
    p50 = list(p50_values.values)
    p90 = list(p90_values.values)

    fig = go.Figure()

    # Band
    fig.add_trace(go.Scatter(
        x=t + t[::-1],
        y=p90 + p10[::-1],
        fill="toself",
        fillcolor=_BAND_FILL,
        line=dict(color="rgba(0,0,0,0)"),
        name="P10–P90",
        hoverinfo="skip",
    ))

    for vals, name, color, dash in [
        (p10, "P10", _P10_LINE, "dash"),
        (p50, "P50", _P50_LINE, "solid"),
        (p90, "P90", _P90_LINE, "dash"),
    ]:
        fig.add_trace(go.Scatter(
            x=t, y=vals,
            mode="lines+markers",
            line=dict(color=color, dash=dash, width=1.5),
            marker=dict(size=5),
            name=name,
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title=str(snapshot_times.unit),
        yaxis_title=y_label,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, l=60, r=20, b=50),
    )
    return fig