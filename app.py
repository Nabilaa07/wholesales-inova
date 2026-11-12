"""Dashboard interaktif Wholesale Toyota Kijang Innova 2017-2026.

Arsitektur data tetap dipertahankan:
- MySQL: fakta transaksi wholesale.
- PostgreSQL: dimensi, katalog varian, kalender, dan referensi peristiwa.
- pandas: integrasi antardatabase di level aplikasi.
- Streamlit + Plotly: antarmuka dashboard interaktif.

UI dirancang ulang agar menyerupai dashboard pada referensi: sidebar bersih,
header ringkas, hero banner, kartu KPI, panel grafik, tabel, dan insight rail.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import charts
import pipeline
from db import get_mysql_engine, get_postgres_engine, ping


# ---------------------------------------------------------------------------
# Konfigurasi halaman
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Innova Wholesale Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Design system dan ikon SVG (Lucide-style, open source)
# ---------------------------------------------------------------------------
ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>',
    "database": '<ellipse cx="12" cy="5" rx="8.5" ry="3"/><path d="M3.5 5v7c0 1.7 3.8 3 8.5 3s8.5-1.3 8.5-3V5"/><path d="M3.5 12v7c0 1.7 3.8 3 8.5 3s8.5-1.3 8.5-3v-7"/>',
    "network": '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M6 16v-4h12v4"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/><path d="M8 7h8M8 11h8"/>',
    "filter": '<polygon points="4 5 20 5 14 12 14 19 10 21 10 12 4 5"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "car": '<path d="m5 11 1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11"/><path d="M3 11h18l1 3v5h-2v-2H4v2H2v-5l1-3Z"/><circle cx="6.5" cy="14" r="1"/><circle cx="17.5" cy="14" r="1"/>',
    "chart": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    "arrow-up-right": '<path d="M7 17 17 7M7 7h10v10"/>',
    "logout": '<path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/>',
}


def svg_icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    """Menghasilkan ikon outline sederhana dengan gaya Lucide."""
    body = ICONS.get(name, ICONS["layers"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{body}</svg>'
    )


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

      :root {
        --ink: #202226;
        --muted: #858991;
        --line: #eceef1;
        --surface: #ffffff;
        --canvas: #eef0f2;
        --accent: #ee9b22;
        --accent-strong: #f4a11f;
        --green: #269b65;
      }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      [data-testid="stAppViewContainer"] { background: var(--canvas); }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stToolbar"] { right: 1rem; }
      [data-testid="stMain"] { background: transparent; }
      .block-container {
        max-width: 1680px;
        padding: 1.35rem 1.5rem 2.2rem;
      }
      section[data-testid="stSidebar"] {
        background: #fff;
        border-right: 1px solid #eaedf0;
        min-width: 245px;
        max-width: 245px;
      }
      section[data-testid="stSidebar"] > div { padding: 1.25rem 1rem 1.5rem; }
      section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .55rem; }
      section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0; }
      section[data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 40px;
        border-radius: 10px;
        border: 1px solid transparent;
        background: transparent;
        color: #3e4248;
        font-size: 13px;
        font-weight: 500;
        text-align: left;
        box-shadow: none;
        padding: .45rem .6rem;
      }
      section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(105deg, #f5a51e, #f08a19);
        color: #fff;
        border-color: transparent;
      }
      section[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        border-color: #f3d6ad;
        color: #a86412;
      }
      section[data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 11px;
        background: #fff;
      }
      section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        font-size: 12px;
        font-weight: 600;
      }

      .brand-wrap { display:flex; align-items:center; gap:10px; padding: 2px 4px 22px; }
      .brand-mark {
        width:36px; height:36px; border-radius:11px; display:flex; align-items:center;
        justify-content:center; color:#dc8c1b; background:#fff5e8;
      }
      .brand-name { color:#202226; font-family:'Manrope',sans-serif; font-size:17px; font-weight:800; line-height:1.1; }
      .brand-sub { color:#a0a4aa; font-size:9px; letter-spacing:1.2px; margin-top:4px; font-weight:700; }
      .side-label { color:#a0a4aa; font-size:9px; letter-spacing:1.2px; font-weight:700; margin: 8px 4px 5px; }
      .side-icon { height:39px; display:flex; align-items:center; justify-content:center; color:#777d85; }
      .side-footer { border-top:1px solid #f0f1f3; margin-top:24px; padding:17px 4px 0; color:#9a9ea5; font-size:10px; line-height:1.7; }

      .topbar { display:flex; align-items:center; justify-content:space-between; margin: 2px 0 17px; }
      .top-eyebrow { color:#9a9ea5; font-size:9px; font-weight:700; letter-spacing:1.35px; margin-bottom:4px; }
      .page-title { color:var(--ink); font-family:'Manrope',sans-serif; font-size:27px; font-weight:700; letter-spacing:-.8px; line-height:1.15; }
      .top-profile { display:flex; align-items:center; justify-content:flex-end; gap:10px; color:#777d85; font-size:11px; }
      .profile-dot { width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#25282d; color:white; font-size:10px; font-weight:700; }
      .status-pill { display:inline-flex; align-items:center; gap:6px; padding:7px 10px; border:1px solid #e8efe9; background:#f6fbf7; color:#39845e; border-radius:999px; font-size:10px; font-weight:600; }
      .status-dot { width:6px; height:6px; border-radius:50%; background:#31a46d; }

      .hero {
        position:relative; overflow:hidden; min-height:105px; border-radius:13px;
        background: radial-gradient(circle at 72% 120%, rgba(207,105,28,.62), transparent 28%),
                    radial-gradient(circle at 88% 5%, rgba(168,83,20,.56), transparent 25%),
                    linear-gradient(105deg,#17100b 0%,#28160e 55%,#120e0c 100%);
        color:white; padding:21px 25px; display:flex; flex-direction:column; justify-content:center;
      }
      .hero:before, .hero:after { content:''; position:absolute; border:1px solid rgba(238,151,52,.45); border-radius:50%; pointer-events:none; }
      .hero:before { width:250px; height:250px; right:90px; top:-160px; box-shadow:0 0 0 22px rgba(234,143,38,.035),0 0 0 45px rgba(234,143,38,.025); }
      .hero:after { width:175px; height:175px; right:8px; top:-85px; box-shadow:0 0 0 18px rgba(234,143,38,.04); }
      .hero-kicker { position:relative; z-index:1; color:#efb567; font-size:9px; letter-spacing:1.45px; font-weight:700; margin-bottom:7px; }
      .hero-title { position:relative; z-index:1; max-width:530px; font-family:'Manrope',sans-serif; font-size:19px; line-height:1.35; letter-spacing:-.35px; font-weight:700; }
      .hero-caption { position:relative; z-index:1; color:#c7bdb5; font-size:10px; margin-top:5px; }
      .date-chip { display:flex; align-items:center; gap:8px; padding:10px 11px; border:1px solid #e8e9eb; border-radius:10px; color:#5d6269; font-size:10px; background:#fff; }

      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #eceef1 !important;
        border-radius: 13px !important;
        background: #fff !important;
        box-shadow: 0 2px 9px rgba(29,35,42,.018);
      }
      [data-testid="stMetric"] { padding: 1px 0; }
      [data-testid="stMetricLabel"] { color:#626770 !important; font-size:10px !important; font-weight:500 !important; }
      [data-testid="stMetricValue"] { color:#202226 !important; font-family:'Manrope',sans-serif; font-size:25px !important; font-weight:800 !important; letter-spacing:-.8px; }
      [data-testid="stMetricDelta"] { font-size:9px !important; }
      .card-heading { display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }
      .card-title { font-family:'Manrope',sans-serif; color:#282b30; font-size:13px; font-weight:700; }
      .card-subtitle { color:#9a9ea5; font-size:9px; margin-top:3px; }
      .mini-label { color:#9a9ea5; font-size:9px; }
      .mix-item { display:flex; justify-content:space-between; gap:8px; color:#535861; font-size:10px; margin:12px 0 4px; }
      .mix-value { color:#25282d; font-weight:700; }
      .insight-box { border-radius:10px; background:#fff8ee; padding:11px 12px; color:#78501d; font-size:10px; line-height:1.55; }
      .table-heading { font-family:'Manrope',sans-serif; font-size:13px; font-weight:700; color:#282b30; }
      .table-note { color:#969ba3; font-size:9px; margin-top:3px; }
      .section-spacer { height:4px; }

      .stButton > button, .stDownloadButton > button {
        border-radius:9px; font-size:11px; font-weight:600; min-height:36px;
        border:1px solid #e6e8eb; box-shadow:none;
      }
      .stDownloadButton > button[kind="primary"], .stButton > button[kind="primary"] {
        background:linear-gradient(105deg,#f5a51e,#f08a19); border-color:transparent; color:white;
      }
      .stSelectbox label, .stMultiSelect label, .stSlider label, .stTextInput label, .stToggle label {
        color:#656a72; font-size:10px; font-weight:600;
      }
      [data-testid="stDataFrame"] { border:1px solid #eff0f2; border-radius:10px; overflow:hidden; }
      [data-testid="stTabs"] button { font-size:11px; }
      [data-testid="stAlert"] { border-radius:11px; }
      footer { visibility:hidden; }

      @media (max-width: 900px) {
        .block-container { padding: 1rem .8rem 1.5rem; }
        .page-title { font-size:23px; }
        .hero-title { font-size:16px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Utilitas tampilan
# ---------------------------------------------------------------------------
def fmt_int(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def card_heading(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f'<div class="card-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="card-heading"><div><div class="card-title">{title}</div>{subtitle_html}</div></div>',
        unsafe_allow_html=True,
    )


def polish_figure(fig, height: int = 300):
    """Samakan tampilan Plotly agar menyatu dengan kartu dashboard."""
    try:
        fig.update_layout(
            height=height,
            autosize=True,
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            font={"family": "DM Sans, sans-serif", "color": "#656a72", "size": 10},
            margin={"l": 8, "r": 8, "t": 12, "b": 8},
            legend={"font": {"size": 9}},
        )
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont={"size": 9})
        fig.update_yaxes(gridcolor="#f0f1f3", zeroline=False, tickfont={"size": 9})
    except Exception:
        pass
    return fig


def show_chart(fig, height: int = 300, key: str | None = None) -> None:
    st.plotly_chart(
        polish_figure(fig, height),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
        key=key,
    )


# ---------------------------------------------------------------------------
# Ambil dan integrasikan data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Mengambil data dari MySQL dan PostgreSQL ...")
def load_data():
    frames = pipeline.extract(get_mysql_engine(), get_postgres_engine())
    df, report = pipeline.integrate(frames)
    events = pipeline.prepare_events(frames["event"])
    return frames, df, report, events


try:
    frames, df_all, report, events = load_data()
except Exception as exc:
    st.error(
        f"Gagal terhubung atau membaca database ({type(exc).__name__}). "
        "Pastikan MySQL dan PostgreSQL aktif, kredensial (.env / Secrets) benar, "
        "serta `python database/seed_data.py` sudah dijalankan."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar: identitas, navigasi, dan filter
# ---------------------------------------------------------------------------
if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"

with st.sidebar:
    st.markdown(
        f'''<div class="brand-wrap">
          <div class="brand-mark">{svg_icon("car", 22, "#dc8c1b")}</div>
          <div><div class="brand-name">Innova</div><div class="brand-sub">WHOLESALE INSIGHT</div></div>
        </div>''',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">MENU UTAMA</div>', unsafe_allow_html=True)

    nav_items = [
        ("Dashboard", "dashboard"),
        ("Data & Pipeline", "database"),
        ("Arsitektur", "network"),
        ("Sumber & Referensi", "book"),
    ]
    for label, icon_name in nav_items:
        icon_col, button_col = st.columns([0.18, 0.82], gap="small", vertical_alignment="center")
        with icon_col:
            icon_color = "#d88b1e" if st.session_state.active_page == label else "#81868e"
            st.markdown(
                f'<div class="side-icon">{svg_icon(icon_name, 17, icon_color)}</div>',
                unsafe_allow_html=True,
            )
        with button_col:
            if st.button(
                label,
                key=f"nav_{label}",
                type="primary" if st.session_state.active_page == label else "secondary",
                width="stretch",
            ):
                st.session_state.active_page = label
                st.rerun()

    st.markdown('<div class="side-label" style="margin-top:20px">FILTER DATA</div>', unsafe_allow_html=True)
    y_min, y_max = int(df_all["year"].min()), int(df_all["year"].max())
    with st.expander("Persempit data", expanded=False):
        years = st.slider("Rentang tahun", y_min, y_max, (y_min, y_max), key="filter_years")

        def multi_filter(label: str, col: str):
            options = sorted(df_all[col].dropna().unique().tolist(), key=lambda x: str(x))
            return st.multiselect(label, options, default=options, key=f"filter_{col}")

        models = multi_filter("Model", "model")
        fuels = multi_filter("Bahan bakar", "fuel_type")
        transmissions = multi_filter("Transmisi", "transmission")
        trims = multi_filter("Tipe", "trim_type")
        sub_types = multi_filter("Sub-tipe", "sub_type")
        search_variant = st.text_input("Cari varian", placeholder="Contoh: Zenix ...")
        show_events = st.toggle("Tampilkan anotasi peristiwa", value=True)

    if "years" not in locals():
        years = (y_min, y_max)
        models = sorted(df_all["model"].dropna().unique().tolist())
        fuels = sorted(df_all["fuel_type"].dropna().unique().tolist())
        transmissions = sorted(df_all["transmission"].dropna().unique().tolist())
        trims = sorted(df_all["trim_type"].dropna().unique().tolist())
        sub_types = sorted(df_all["sub_type"].dropna().unique().tolist())
        search_variant = ""
        show_events = True

    st.markdown(
        '<div class="side-footer">Sumber data<br><b style="color:#626770">MySQL</b> · Fakta wholesale<br>'
        '<b style="color:#626770">PostgreSQL</b> · Dimensi dan referensi<br><br>Dashboard internal · 2017–2026</div>',
        unsafe_allow_html=True,
    )


# Terapkan filter global.
df = df_all[
    df_all["year"].between(*years)
    & df_all["model"].isin(models)
    & df_all["fuel_type"].isin(fuels)
    & df_all["transmission"].isin(transmissions)
    & df_all["trim_type"].isin(trims)
    & df_all["sub_type"].isin(sub_types)
].copy()
if search_variant:
    df = df[df["variant_label"].astype(str).str.contains(search_variant, case=False, na=False)]


# ---------------------------------------------------------------------------
# Header bersama
# ---------------------------------------------------------------------------
def render_header(title: str, subtitle: str) -> None:
    left, right = st.columns([7, 2], vertical_alignment="center")
    with left:
        st.markdown(
            f'<div class="topbar"><div><div class="top-eyebrow">WHOLESALE ANALYTICS / TOYOTA</div>'
            f'<div class="page-title">{title}</div></div></div>',
            unsafe_allow_html=True,
        )
        st.caption(subtitle)
    with right:
        st.markdown(
            f'''<div class="top-profile">
              <span style="color:#858991">{svg_icon("bell", 17, "#777d85")}</span>
              <span class="profile-dot">IK</span>
              <span><b style="color:#34383e;font-size:11px">Innova Data</b><br><span style="font-size:9px;color:#a0a4aa">Wholesale analyst</span></span>
            </div>''',
            unsafe_allow_html=True,
        )


def render_hero(download_data: bytes) -> None:
    banner_col, action_col = st.columns([4.5, 1.05], vertical_alignment="top")
    with banner_col:
        st.markdown(
            '''<div class="hero">
              <div class="hero-kicker">WHOLESALE PERFORMANCE OVERVIEW</div>
              <div class="hero-title">Pahami pergerakan distribusi Toyota Kijang Innova.</div>
              <div class="hero-caption">Pantau tren, komposisi varian, dan performa wholesale dari 2017 hingga 2026.</div>
            </div>''',
            unsafe_allow_html=True,
        )
    with action_col:
        st.download_button(
            "Unduh laporan",
            data=download_data,
            file_name="innova_wholesale_report.csv",
            mime="text/csv",
            type="primary",
            width="stretch",
        )
        st.markdown(
            f'<div class="date-chip">{svg_icon("calendar", 15, "#d18a26")} Data {int(df["year"].min())}–{int(df["year"].max())}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Halaman: Dashboard
# ---------------------------------------------------------------------------
def render_dashboard() -> None:
    if df.empty:
        st.warning("Tidak ada data untuk kombinasi filter ini. Longgarkan filter pada sidebar.")
        return

    total = int(df["units"].sum())
    monthly = df.groupby("period_date")["units"].sum()
    peak_date, peak_val = monthly.idxmax(), int(monthly.max())
    top_variant = df.groupby("variant_label")["units"].sum().idxmax()

    last = df["period_date"].max()
    latest_year, latest_month = int(last.year), int(last.month)
    current_ytd = int(df[(df["year"] == latest_year) & (df["month_num"] <= latest_month)]["units"].sum())
    previous_ytd = int(df[(df["year"] == latest_year - 1) & (df["month_num"] <= latest_month)]["units"].sum())
    ytd_delta = f"{(current_ytd - previous_ytd) / previous_ytd * 100:+.1f}% vs {latest_year - 1}" if previous_ytd else None

    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    render_hero(csv_data)
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # KPI cards
    k1, k2, k3, k4 = st.columns(4, gap="small")
    with k1:
        with st.container(border=True):
            st.metric("Total wholesale", fmt_int(total), help="Total unit wholesale sesuai filter aktif.")
            st.caption("Akumulasi seluruh periode terpilih")
    with k2:
        with st.container(border=True):
            st.metric(f"YTD {latest_year}", fmt_int(current_ytd), ytd_delta)
            st.caption(f"Januari–{last:%b} {latest_year}")
    with k3:
        with st.container(border=True):
            st.metric("Bulan tertinggi", peak_date.strftime("%b %Y"), delta=f"{fmt_int(peak_val)} unit", delta_color="off")
            st.caption("Volume wholesale bulanan terbesar")
    with k4:
        with st.container(border=True):
            st.metric("Varian terlaris", top_variant.split(" - ")[0][:22], help=top_variant)
            st.caption("Varian dengan total unit tertinggi")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # Tren bulanan + komposisi model
    trend_col, insight_col = st.columns([2.25, 1], gap="small")
    with trend_col:
        with st.container(border=True):
            head_l, head_r = st.columns([1.6, 1], vertical_alignment="center")
            with head_l:
                card_heading("Tren wholesale", "Pergerakan unit per bulan")
            with head_r:
                group_options = ["Total", "Model", "Bahan bakar", "Transmisi", "Tipe", "Powertrain"]
                group_choice = st.selectbox("Kelompok", group_options, index=0, label_visibility="collapsed", key="trend_group")
            group_map = {
                "Model": "model", "Bahan bakar": "fuel_type", "Transmisi": "transmission",
                "Tipe": "trim_type", "Powertrain": "powertrain",
            }
            trend_fig = charts.monthly_trend(df, group_map.get(group_choice), events if show_events else None)
            show_chart(trend_fig, height=300, key="monthly_trend_chart")
    with insight_col:
        with st.container(border=True):
            card_heading("Komposisi model", "Kontribusi terhadap total unit")
            model_mix = df.groupby("model")["units"].sum().sort_values(ascending=False).head(5)
            for model_name, units in model_mix.items():
                share = float(units / total * 100) if total else 0
                st.markdown(
                    f'<div class="mix-item"><span>{model_name}</span><span class="mix-value">{share:.1f}%</span></div>',
                    unsafe_allow_html=True,
                )
                st.progress(min(max(share / 100, 0.0), 1.0), text=None)
            st.markdown(
                f'<div class="insight-box" style="margin-top:14px"><b>Varian unggulan</b><br>{top_variant}<br>'
                f'<span style="color:#9a733e">{fmt_int(int(df.groupby("variant_label")["units"].sum().max()))} unit pada filter aktif</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # Perbandingan tahunan dan varian teratas
    annual_col, variant_col = st.columns([1.25, 1], gap="small")
    with annual_col:
        with st.container(border=True):
            head_l, head_r = st.columns([1.5, 1], vertical_alignment="center")
            with head_l:
                card_heading("Perbandingan tahunan", "Total unit berdasarkan tahun")
            with head_r:
                annual_group = st.selectbox(
                    "Dimensi", ["Model", "Bahan bakar", "Transmisi", "Tipe", "Powertrain"],
                    label_visibility="collapsed", key="annual_group",
                )
            annual_map = {
                "Model": "model", "Bahan bakar": "fuel_type", "Transmisi": "transmission",
                "Tipe": "trim_type", "Powertrain": "powertrain",
            }
            show_chart(charts.yearly_bar(df, annual_map[annual_group]), height=300, key="yearly_bar_chart")
            st.caption("Tahun 2026 baru mencakup data yang tersedia; bandingkan dengan mempertimbangkan periode parsial.")
    with variant_col:
        with st.container(border=True):
            head_l, head_r = st.columns([1.3, 1], vertical_alignment="center")
            with head_l:
                card_heading("Varian teratas", "Peringkat berdasarkan total unit")
            with head_r:
                top_n = st.selectbox("Jumlah", [5, 8, 10, 15, 20], index=2, label_visibility="collapsed", key="top_variant_n")
            show_chart(charts.top_variants(df, top_n), height=300, key="top_variants_chart")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # Ringkasan varian dan gauge kontribusi tahun terbaru
    table_col, gauge_col = st.columns([2.25, 1], gap="small")
    with table_col:
        with st.container(border=True):
            top_table_head, top_table_action = st.columns([2, 1], vertical_alignment="center")
            with top_table_head:
                st.markdown('<div class="table-heading">Top selling variants</div><div class="table-note">Ringkasan varian berdasarkan unit wholesale</div>', unsafe_allow_html=True)
            with top_table_action:
                st.download_button(
                    "Unduh CSV",
                    data=csv_data,
                    file_name="innova_wholesale_filtered.csv",
                    mime="text/csv",
                    width="stretch",
                )
            table = (
                df.groupby(["variant_label", "model", "fuel_type", "transmission"], dropna=False)["units"]
                .sum().reset_index().sort_values("units", ascending=False).head(8)
            )
            table["Kontribusi"] = (table["units"] / total * 100).map(lambda x: f"{x:.1f}%" if total else "0.0%")
            table = table.rename(columns={
                "variant_label": "Varian", "model": "Model", "fuel_type": "Bahan bakar",
                "transmission": "Transmisi", "units": "Unit",
            })
            table["Unit"] = table["Unit"].map(fmt_int)
            st.dataframe(table, width="stretch", hide_index=True, height=315)
    with gauge_col:
        with st.container(border=True):
            card_heading("Kontribusi tahun terbaru", f"Porsi {latest_year} dari seluruh unit terfilter")
            latest_units = int(df.loc[df["year"] == latest_year, "units"].sum())
            latest_share = latest_units / total * 100 if total else 0
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=latest_share,
                number={"suffix": "%", "font": {"size": 27, "color": "#25282d", "family": "Manrope"}},
                gauge={
                    "shape": "angular",
                    "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)", "visible": False},
                    "bar": {"color": "#ee9b22", "thickness": .28},
                    "bgcolor": "#f1f2f4",
                    "borderwidth": 0,
                    "steps": [{"range": [0, 100], "color": "#f3f4f6"}],
                },
            ))
            gauge.update_layout(height=205, margin={"l": 15, "r": 15, "t": 15, "b": 0}, paper_bgcolor="rgba(255,255,255,0)")
            st.plotly_chart(gauge, width="stretch", config={"displayModeBar": False}, key="latest_year_gauge")
            st.markdown(
                f'<div class="insight-box"><b>{fmt_int(latest_units)} unit</b> tercatat pada {latest_year}. '
                f'Angka ini merupakan {latest_share:.1f}% dari total unit pada filter saat ini.</div>',
                unsafe_allow_html=True,
            )

    with st.expander("Analisis komposisi dan pola musiman", expanded=False):
        comp_tab, season_tab = st.tabs(["Komposisi", "Musiman"])
        with comp_tab:
            c1, c2 = st.columns(2)
            with c1:
                card_heading("Peta komposisi", "Hierarki model dan varian")
                show_chart(charts.sunburst(df), height=370, key="sunburst_chart")
            with c2:
                card_heading("Pangsa model dari waktu ke waktu")
                show_chart(charts.model_share_area(df), height=370, key="model_share_chart")
        with season_tab:
            s1, s2 = st.columns(2)
            with s1:
                card_heading("Heatmap musiman")
                show_chart(charts.seasonality_heatmap(df), height=370, key="season_heatmap")
            with s2:
                card_heading("Rata-rata unit per bulan")
                show_chart(charts.avg_by_month(df), height=370, key="season_average")


# ---------------------------------------------------------------------------
# Halaman: Data & Pipeline
# ---------------------------------------------------------------------------
def render_data_page() -> None:
    render_header("Data & Pipeline", "Validasi integrasi fakta MySQL dengan dimensi PostgreSQL")
    if df.empty:
        st.warning("Tidak ada data untuk kombinasi filter ini. Longgarkan filter pada sidebar.")
        return

    r = report
    st.markdown('<div class="card-heading"><div class="card-title">Status integrasi database</div></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="small")
    for col, label, value in [
        (c1, "Baris fakta · MySQL", r.rows_fact_mysql),
        (c2, "Dimensi varian · PostgreSQL", r.rows_dim_variant_pg),
        (c3, "Dimensi periode · PostgreSQL", r.rows_dim_period_pg),
        (c4, "Baris setelah merge", r.rows_merged),
    ]:
        with col:
            with st.container(border=True):
                st.metric(label, fmt_int(value))
    if r.ok:
        st.success(f"Join valid: tidak ada baris tanpa pasangan; total unit sebelum dan sesudah merge = {fmt_int(r.units_before)}.")
    else:
        st.error("Join tidak konsisten. Periksa seed data dan relasi kunci antara kedua database.")

    csv_columns = [
        "period_date", "year", "month_name", "model", "fuel_type", "transmission",
        "trim_type", "sub_type", "units", "source_row",
    ]
    available_columns = [c for c in csv_columns if c in df.columns]
    csv_data = df[available_columns].to_csv(index=False).encode("utf-8-sig")
    head_l, head_r = st.columns([3, 1], vertical_alignment="center")
    with head_l:
        card_heading("Data terintegrasi", "Hasil pandas.merge() berdasarkan filter aktif")
    with head_r:
        st.download_button("Unduh data terfilter", csv_data, "innova_wholesale_filtered.csv", "text/csv", width="stretch")
    st.dataframe(df[available_columns], width="stretch", hide_index=True, height=440)

    with st.expander("Lihat sampel data mentah dari tiap DBMS"):
        raw1, raw2, raw3 = st.tabs(["MySQL · fact_wholesale", "PostgreSQL · dim_variant", "PostgreSQL · dim_period"])
        with raw1:
            st.dataframe(frames["fact"].head(20), width="stretch", hide_index=True)
        with raw2:
            st.dataframe(frames["variant"].head(20), width="stretch", hide_index=True)
        with raw3:
            st.dataframe(frames["period"].head(20), width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Halaman: Arsitektur
# ---------------------------------------------------------------------------
def render_architecture_page() -> None:
    render_header("Arsitektur sistem", "Alur ekstraksi, integrasi, dan visualisasi data wholesale")
    my_ok, my_ver = ping(get_mysql_engine())
    pg_ok, pg_ver = ping(get_postgres_engine())
    c1, c2 = st.columns(2, gap="small")
    with c1:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">{svg_icon("database", 16, "#d58b24")} &nbsp;DBMS 1 — MySQL</div>', unsafe_allow_html=True)
            st.metric("Status koneksi", "Terhubung" if my_ok else "Gagal", delta_color="off")
            st.caption(str(my_ver)[:120])
    with c2:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">{svg_icon("database", 16, "#d58b24")} &nbsp;DBMS 2 — PostgreSQL</div>', unsafe_allow_html=True)
            st.metric("Status koneksi", "Terhubung" if pg_ok else "Gagal", delta_color="off")
            st.caption(str(pg_ver)[:120])

    with st.container(border=True):
        card_heading("Alur data", "Data dibersihkan sebelum dimuat ke dua sistem database")
        st.graphviz_chart(
            r'''
            digraph G {
              rankdir=LR; bgcolor="transparent"; pad="0.2"; nodesep="0.45"; ranksep="0.6";
              node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10, color="#e3e6e9", margin="0.18,0.12"];
              edge [color="#aeb4bb", penwidth=1.3, arrowsize=0.7, fontname="Arial", fontsize=9];
              csv [label="CSV sumber\nKaggle", fillcolor="#fff1d9"];
              seed [label="seed_data.py\nPembersihan pandas", fillcolor="#f1f3f5"];
              mysql [label="MySQL\nfact_wholesale", fillcolor="#e7f0ff"];
              pg [label="PostgreSQL\ndim_variant · dim_period\nref_market_event", fillcolor="#e8f5ed"];
              merge [label="pipeline.py\npandas.merge()", fillcolor="#f1f3f5"];
              app [label="Streamlit + Plotly\nDashboard interaktif", fillcolor="#fff0e8"];
              csv -> seed; seed -> mysql; seed -> pg;
              mysql -> merge [label="SQL"];
              pg -> merge [label="SQL"];
              merge -> app;
            }
            ''',
        )

    with st.container(border=True):
        card_heading("Pembagian tanggung jawab database")
        st.markdown(
            """
            | Komponen | MySQL | PostgreSQL |
            |---|---|---|
            | **Peran** | Penyimpanan fakta wholesale | Katalog dan referensi master |
            | **Tabel** | `fact_wholesale` | `dim_variant`, `dim_period`, `ref_market_event` |
            | **Kunci integrasi** | `variant_id`, `period_id` | `variant_id`, `period_id` |
            | **Konsumsi data** | Diekstrak melalui SQLAlchemy | Diekstrak melalui SQLAlchemy |
            """
        )
        st.info(
            "Foreign key lintas-DBMS tidak dipaksakan oleh database. Integritas relasi diperiksa di aplikasi "
            "menggunakan merge tervalidasi (misalnya validate='m:1'), indikator pasangan, dan rekonsiliasi jumlah unit."
        )


# ---------------------------------------------------------------------------
# Halaman: Sumber & Referensi
# ---------------------------------------------------------------------------
def render_sources_page() -> None:
    render_header("Sumber & Referensi", "Dataset dan dokumentasi teknologi yang digunakan")
    with st.container(border=True):
        card_heading("Sumber data primer", "Dataset wholesale Toyota Kijang Innova Indonesia")
        st.markdown(
            "[Toyota Innova Wholesale Sales Indonesia 2017–2026 — Kaggle](https://www.kaggle.com/datasets/yonathanhary/toyota-innova-wholesale-sales-indonesia2017-2026/data)"
        )
        st.caption("Data wholesale merepresentasikan distribusi dari pabrik ke dealer.")
    with st.container(border=True):
        card_heading("Dokumentasi teknis")
        references = [
            ("Streamlit — Connect to MySQL", "https://docs.streamlit.io/develop/tutorials/databases/mysql"),
            ("Streamlit — Connect to PostgreSQL", "https://docs.streamlit.io/develop/tutorials/databases/postgresql"),
            ("SQLAlchemy 2.0", "https://docs.sqlalchemy.org/en/20/"),
            ("pandas.DataFrame.merge", "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html"),
            ("Plotly Python", "https://plotly.com/python/"),
        ]
        for label, url in references:
            st.markdown(f"- [{label}]({url})")
    with st.container(border=True):
        card_heading("Catatan implementasi")
        st.markdown(
            "Kode dashboard memanggil modul `pipeline.py`, `charts.py`, dan `db.py`. "
            "Skema SQL serta seed script tetap dikelola terpisah agar UI tidak bercampur dengan logika ekstraksi dan transformasi data."
        )


# ---------------------------------------------------------------------------
# Router halaman
# ---------------------------------------------------------------------------
if st.session_state.active_page == "Dashboard":
    render_header("Dashboard", "Toyota Kijang Innova · Wholesale performance 2017–2026")
    render_dashboard()
elif st.session_state.active_page == "Data & Pipeline":
    render_data_page()
elif st.session_state.active_page == "Arsitektur":
    render_architecture_page()
else:
    render_sources_page()
