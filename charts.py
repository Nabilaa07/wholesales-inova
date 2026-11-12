"""Fungsi pembuat grafik Plotly (tanpa akses database)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#EB0A1E", "#1F2937", "#0EA5A4", "#F59E0B", "#6366F1", "#84CC16", "#EC4899", "#64748B"]
LAYOUT = dict(margin=dict(l=10, r=10, t=50, b=10), legend_title_text="", hovermode="x unified")
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly_trend(df: pd.DataFrame, group: str | None, events: pd.DataFrame | None) -> go.Figure:
    if group:
        data = df.groupby(["period_date", group], as_index=False)["units"].sum()
        fig = px.line(data, x="period_date", y="units", color=group, color_discrete_sequence=PALETTE)
    else:
        data = df.groupby("period_date", as_index=False)["units"].sum()
        fig = px.line(data, x="period_date", y="units", color_discrete_sequence=PALETTE)
    fig.update_traces(line=dict(width=2.2))
    if events is not None and not events.empty and not data.empty:
        lo, hi = data["period_date"].min(), data["period_date"].max()
        for ev in events.itertuples():
            if ev.end_date < lo or ev.start_date > hi:
                continue
            fig.add_vrect(x0=ev.start_date, x1=ev.end_date, fillcolor="#F59E0B", opacity=0.18,
                          line_width=0, annotation_text=ev.event_name, annotation_position="top left",
                          annotation_font_size=11)
    fig.update_layout(title="Tren wholesale bulanan (unit)", xaxis_title="", yaxis_title="Unit", **LAYOUT)
    return fig


def yearly_bar(df: pd.DataFrame, group: str) -> go.Figure:
    data = df.groupby(["year", group], as_index=False)["units"].sum()
    fig = px.bar(data, x="year", y="units", color=group, color_discrete_sequence=PALETTE)
    fig.update_xaxes(type="category", title="")
    fig.update_layout(title="Total wholesale per tahun (unit)", yaxis_title="Unit", barmode="stack", **LAYOUT)
    return fig


def model_share_area(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["year", "model"], as_index=False)["units"].sum()
    data["share"] = data["units"] / data.groupby("year")["units"].transform("sum") * 100
    fig = px.area(data, x="year", y="share", color="model", color_discrete_sequence=PALETTE)
    fig.update_xaxes(type="category", title="")
    fig.update_layout(title="Pergeseran porsi model per tahun (%)", yaxis_title="Porsi (%)", **LAYOUT)
    return fig


def sunburst(df: pd.DataFrame) -> go.Figure:
    path = ["model", "fuel_type", "transmission", "trim_type"]
    data = df.groupby(path, as_index=False)["units"].sum()
    data = data[data["units"] > 0]
    fig = px.sunburst(data, path=path, values="units", color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="label+percent parent")
    fig.update_layout(title="Komposisi varian (klik untuk drill-down)", margin=dict(l=10, r=10, t=50, b=10))
    return fig


def top_variants(df: pd.DataFrame, n: int = 10) -> go.Figure:
    data = (df.groupby("variant_label", as_index=False)["units"].sum()
              .sort_values("units", ascending=False).head(n).sort_values("units"))
    fig = px.bar(data, x="units", y="variant_label", orientation="h", color_discrete_sequence=[PALETTE[0]])
    fig.update_layout(title=f"{n} varian terlaris", xaxis_title="Unit", yaxis_title="",
                      margin=dict(l=10, r=10, t=50, b=10))
    return fig


def seasonality_heatmap(df: pd.DataFrame) -> go.Figure:
    pv = (df.groupby(["year", "month_name"])["units"].sum().unstack("month_name")
            .reindex(columns=[m for m in MONTH_ORDER if m in df["month_name"].unique()]))
    fig = px.imshow(pv, aspect="auto", color_continuous_scale="Reds", text_auto=",.0f")
    fig.update_yaxes(type="category", title="")
    fig.update_layout(title="Heatmap musiman: tahun x bulan (unit)", xaxis_title="",
                      coloraxis_colorbar_title="Unit", margin=dict(l=10, r=10, t=50, b=10))
    return fig


def avg_by_month(df: pd.DataFrame) -> go.Figure:
    per = df.groupby(["year", "month_name"], as_index=False)["units"].sum()
    data = per.groupby("month_name", as_index=False)["units"].mean()
    data["month_name"] = pd.Categorical(data["month_name"], MONTH_ORDER, ordered=True)
    data = data.sort_values("month_name")
    fig = px.bar(data, x="month_name", y="units", color_discrete_sequence=[PALETTE[1]])
    fig.update_layout(title="Rata-rata wholesale per bulan (lintas tahun)", xaxis_title="",
                      yaxis_title="Unit rata-rata", margin=dict(l=10, r=10, t=50, b=10))
    return fig
