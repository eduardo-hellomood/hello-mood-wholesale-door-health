from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

import pandas as pd
import streamlit as st
from streamlit_echarts import JsCode, st_echarts

import wholesale_door_health_queries as queries

st.set_page_config(
    page_title="Wholesale Door Health",
    layout="wide",
)

_US_STATES: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}

_STATUS_ORDER = ["Active", "At Risk", "Churned", "Lost"]
_BORDER_COLOR = {"Active": "#22c55e", "At Risk": "#f59e0b", "Churned": "#ef4444", "Lost": "#9ca3af"}
_TEXT_COLOR   = {"Active": "#16a34a", "At Risk": "#d97706", "Churned": "#dc2626", "Lost": "#6b7280"}
_CHART_COLOR  = {"Active": "#4ade80", "At Risk": "#fbbf24", "Churned": "#f87171", "Lost": "#d1d5db"}
_SUBTITLE     = {
    "Active":  ("ACTIVE — LAST 30 DAYS",  "Doors with recent orders"),
    "At Risk": ("AT RISK — 31–60 DAYS",   "Needs rep outreach"),
    "Churned": ("CHURNED — 61–90 DAYS",   "High churn risk"),
    "Lost":    ("LOST — 90+ DAYS",         "No order in 90+ days"),
}


# ─── Data loaders ─────────────────────────────────────────────────────────────

@st.cache_resource(ttl=600)
def _client():
    return queries.get_client()


_V = "v15"  # bump to bust cache after query changes

@st.cache_data(ttl=1800)
def _summary(as_of: str, v: str = _V) -> dict[str, int]:
    return queries.door_health_summary(_client(), as_of)


@st.cache_data(ttl=1800)
def _trend(v: str = _V) -> pd.DataFrame:
    return queries.monthly_trend(_client())


@st.cache_data(ttl=1800)
def _weekly_trend(v: str = _V) -> pd.DataFrame:
    return queries.weekly_trend(_client())


@st.cache_data(ttl=1800)
def _detail(as_of: str, v: str = _V) -> pd.DataFrame:
    return queries.door_detail(_client(), as_of)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Filters")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    today_et = datetime.now(_ET).date()
    as_of_date = st.date_input(
        "As of date",
        value=today_et,
        max_value=today_et,
    )
    as_of = as_of_date.strftime("%Y-%m-%d")

# ─── Header ───────────────────────────────────────────────────────────────────

col_title, col_meta = st.columns([3, 2])
with col_title:
    st.markdown(
        "<div style='font-size:11px;color:#9ca3af;letter-spacing:1.5px;font-weight:600;"
        "text-transform:uppercase;margin-bottom:2px'>WHOLESALE — SMOKE & VAPE</div>"
        "<div style='font-size:26px;font-weight:700;color:#111827'>Door Health Dashboard</div>",
        unsafe_allow_html=True,
    )
with col_meta:
    st.markdown(
        f"<div style='text-align:right;color:#6b7280;font-size:13px;padding-top:22px'>"
        f"As of {as_of_date.strftime('%B %d, %Y')}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:8px 0 20px;border-color:#e5e7eb'>", unsafe_allow_html=True)

# ─── KPI cards ────────────────────────────────────────────────────────────────

summary = _summary(as_of, _V)
total = sum(summary.values()) or 1

kpi_cols = st.columns(4)
for col, status in zip(kpi_cols, _STATUS_ORDER):
    count = summary.get(status, 0)
    pct = round(count / total * 100)
    label, subtitle = _SUBTITLE[status]
    col.markdown(
        f"<div style='border-left:4px solid {_BORDER_COLOR[status]};padding:14px 18px;"
        f"background:#fff;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,0.07)'>"
        f"<div style='font-size:10px;font-weight:700;letter-spacing:1.2px;color:#6b7280;"
        f"text-transform:uppercase;margin-bottom:4px'>{label}</div>"
        f"<div style='font-size:40px;font-weight:700;color:{_TEXT_COLOR[status]};line-height:1.1'>{count}</div>"
        f"<div style='font-size:12px;color:#6b7280;margin-top:4px'>{subtitle}</div>"
        f"<div style='font-size:12px;font-weight:600;color:{_TEXT_COLOR[status]};margin-top:2px'>"
        f"{pct}% of all doors</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# ─── Charts ───────────────────────────────────────────────────────────────────

chart_l, chart_r = st.columns([6, 4])

with chart_l:
    title_col, toggle_col = st.columns([3, 1], gap="small")
    with toggle_col:
        use_weekly = st.toggle("Weekly", value=False)
    if use_weekly:
        trend = _weekly_trend(_V)
        x_labels = trend["week_label"].tolist()
        chart_title = "**Weekly Door Counts — Total vs. Existing + New**"
    else:
        trend = _trend(_V)
        x_labels = trend["month_label"].tolist()
        chart_title = "**Monthly Door Counts — Total vs. Existing + New**"
    with title_col:
        st.markdown(chart_title)
    existing = (trend["active_doors"] - trend["new_doors"]).tolist()
    new_d    = trend["new_doors"].tolist()
    total    = trend["active_doors"].tolist()
    st_echarts(
        options={
            "tooltip": {"trigger": "axis"},
            "legend": {
                "data": ["Total Active", "Existing Doors", "New Doors"],
                "bottom": 0, "itemHeight": 10, "textStyle": {"fontSize": 11},
            },
            "grid": {"top": 10, "bottom": 50, "left": 50, "right": 50},
            "xAxis": {"type": "category", "data": x_labels, "axisLabel": {"fontSize": 11}},
            "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#f3f4f6"}}},
            "series": [
                {"name": "Total Active", "type": "bar", "data": total,
                 "itemStyle": {"color": "#1e3a5f"}, "barGap": "20%",
                 "label": {"show": True, "position": "top", "fontSize": 11, "fontWeight": "bold", "color": "#374151"}},
                {"name": "Existing Doors", "type": "bar", "stack": "composition",
                 "data": existing, "itemStyle": {"color": "#22c55e"},
                 "label": {"show": True, "position": "inside", "fontSize": 10, "color": "#fff"}},
                {"name": "New Doors", "type": "bar", "stack": "composition",
                 "data": new_d, "itemStyle": {"color": "#93c5fd"},
                 "label": {"show": True, "position": "top", "fontSize": 10, "color": "#374151"}},
            ],
        },
        height="280px",
    )

with chart_r:
    st.markdown("**Door Health Distribution**")
    st_echarts(
        options={
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {
                "orient": "horizontal", "bottom": 0, "left": "center",
                "itemHeight": 10, "textStyle": {"fontSize": 11},
            },
            "series": [{
                "type": "pie",
                "radius": ["42%", "65%"],
                "center": ["50%", "45%"],
                "label": {"show": True, "position": "inside", "fontSize": 9, "fontWeight": "bold", "color": "#fff",
                           "formatter": JsCode("function(p){return p.value+'\\n('+p.percent.toFixed(1)+'%)'}")},
                "emphasis": {"itemStyle": {"shadowBlur": 8, "shadowColor": "rgba(0,0,0,0.15)"}},
                "data": [
                    {"name": f"{s} ({['≤30d','31-60d','61-90d','90+d'][i]})",
                     "value": summary.get(s, 0),
                     "itemStyle": {"color": _CHART_COLOR[s]}}
                    for i, s in enumerate(_STATUS_ORDER)
                ],
            }],
        },
        height="280px",
    )

# ─── Door detail table ────────────────────────────────────────────────────────

detail = _detail(as_of, _V)

st.markdown(
    f"<div style='font-size:16px;font-weight:700;margin-bottom:10px'>"
    f"Door Detail View "
    f"<span style='float:right;font-size:13px;color:#6b7280;font-weight:400'>"
    f"{len(detail)} total doors</span></div>",
    unsafe_allow_html=True,
)

f1, f2, f3, _, f4 = st.columns([2, 2, 2, 1, 3])
with f1:
    reps = ["All Reps"] + sorted(detail["rep"].dropna().unique().tolist())
    rep_sel = st.selectbox("Rep", reps, label_visibility="collapsed")
with f2:
    status_sel = st.selectbox("Status", ["All"] + _STATUS_ORDER, label_visibility="collapsed")
with f3:
    regions = ["All Regions"] + sorted(detail["state"].dropna().unique().tolist())
    region_sel = st.selectbox("Region", regions, label_visibility="collapsed")
with f4:
    search = st.text_input("search", placeholder="Search door name...", label_visibility="collapsed")

df = detail.copy()
if rep_sel != "All Reps":
    df = df[df["rep"] == rep_sel]
if status_sel != "All":
    df = df[df["status"] == status_sel]
if region_sel != "All Regions":
    df = df[df["state"] == region_sel]
if search:
    df = df[df["door_name"].str.contains(search, case=False, na=False)]

# Build display dataframe
def _city_state(row: pd.Series) -> str:
    abbr = _US_STATES.get(row["state"], row["state"][:2].upper() if pd.notna(row["state"]) else "")
    city = row["city"] if pd.notna(row["city"]) else ""
    return f"{city}, {abbr}" if city else abbr

display = pd.DataFrame({
    "Company Name":     df["company"].fillna(""),
    "Door Name":        df["door_name"],
    "City / State":     df.apply(_city_state, axis=1),
    "Rep":              df["rep"].fillna(""),
    "Last Order":       pd.to_datetime(df["last_order_date"]),
    "Days Since Order": df["days_since_order"].astype(int),
    "Status":           df["status"],
    "Spend (Last 90d)": df["spend_30d"],
    "Total Spend":      df["spend_total"],
})

_STATUS_BG = {"Active": "#dcfce7", "At Risk": "#fef3c7", "Churned": "#fee2e2", "Lost": "#f3f4f6"}
_DAYS_BG   = lambda d: "#dcfce7" if d <= 30 else "#fef3c7" if d <= 60 else "#fee2e2" if d <= 90 else "#f3f4f6"

def _style(df: pd.DataFrame) -> pd.DataFrame:
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    styles["Status"]           = df["Status"].map(lambda s: f"background-color:{_STATUS_BG.get(s,'')};font-weight:600")
    styles["Days Since Order"] = df["Days Since Order"].map(lambda d: f"background-color:{_DAYS_BG(d)};font-weight:500")
    styles["Spend (Last 90d)"] = df["Spend (Last 90d)"].map(lambda v: "color:#6b7280" if v == 0 else "")
    return styles

st.dataframe(
    display.style.apply(_style, axis=None),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Last Order":       st.column_config.DateColumn("Last Order", format="MMM DD, YYYY"),
        "Spend (Last 90d)": st.column_config.NumberColumn("Spend (Last 90d)", format="$%,.0f"),
        "Total Spend":      st.column_config.NumberColumn("Total Spend", format="$%,.0f"),
        "Days Since Order": st.column_config.NumberColumn("Days Since Order"),
    },
    height=500,
)
