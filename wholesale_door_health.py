from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

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


@st.cache_data(ttl=1800)
def _summary() -> dict[str, int]:
    return queries.door_health_summary(_client())


@st.cache_data(ttl=1800)
def _trend() -> pd.DataFrame:
    return queries.monthly_trend(_client())


@st.cache_data(ttl=1800)
def _detail() -> pd.DataFrame:
    return queries.door_detail(_client())


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
        f"As of {date.today().strftime('%B %d, %Y')}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:8px 0 20px;border-color:#e5e7eb'>", unsafe_allow_html=True)

# ─── KPI cards ────────────────────────────────────────────────────────────────

summary = _summary()
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
trend = _trend()

with chart_l:
    st.markdown("**Monthly Door Counts — Total vs. Existing + New**")
    existing = (trend["active_doors"] - trend["new_doors"]).tolist()
    new_d    = trend["new_doors"].tolist()
    total    = trend["active_doors"].tolist()
    months   = trend["month_label"].tolist()
    st_echarts(
        options={
            "tooltip": {"trigger": "axis"},
            "legend": {
                "data": ["Total Active", "Existing Doors", "New Doors"],
                "bottom": 0, "itemHeight": 10, "textStyle": {"fontSize": 11},
            },
            "grid": {"top": 10, "bottom": 50, "left": 50, "right": 50},
            "xAxis": {"type": "category", "data": months, "axisLabel": {"fontSize": 11}},
            "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#f3f4f6"}}},
            "series": [
                {"name": "Total Active", "type": "bar", "data": total,
                 "itemStyle": {"color": "#bbf7d0"}, "barGap": "20%",
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
    st.markdown("**Door Health Distribution This Month**")
    st_echarts(
        options={
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {
                "orient": "vertical", "right": "2%", "top": "center",
                "itemHeight": 10, "textStyle": {"fontSize": 11},
            },
            "series": [{
                "type": "pie",
                "radius": ["42%", "68%"],
                "center": ["38%", "50%"],
                "label": {"show": True, "position": "outside", "formatter": "{b|{b}}\n{c|{c}}", "rich": {"b": {"fontSize": 10, "color": "#6b7280"}, "c": {"fontSize": 11, "fontWeight": "bold", "color": "#111827"}}},
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

detail = _detail()

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


def _days_color(d: int) -> str:
    if d <= 30:  return "#16a34a"
    if d <= 60:  return "#d97706"
    if d <= 90:  return "#dc2626"
    return "#6b7280"


rows_html = ""
for _, row in df.iterrows():
    abbr = _US_STATES.get(row["state"], row["state"][:2].upper() if pd.notna(row["state"]) else "")
    city = row["city"] if pd.notna(row["city"]) else ""
    city_state = f"{city}, {abbr}" if city else abbr
    last_date = pd.to_datetime(row["last_order_date"]).strftime("%b %d, %Y") if pd.notna(row["last_order_date"]) else "—"
    days = int(row["days_since_order"])
    spend = f"${row['monthly_spend']:,.0f}" if row["monthly_spend"] > 0 else "$0"
    dc = _days_color(days)
    tc = _TEXT_COLOR.get(row["status"], "#374151")
    rows_html += (
        f"<tr style='border-bottom:1px solid #f3f4f6'>"
        f"<td style='padding:10px 12px;font-weight:600'>{row['door_name']}</td>"
        f"<td style='padding:10px 12px;color:#6b7280'>{city_state}</td>"
        f"<td style='padding:10px 12px'>{row.get('rep', '') or ''}</td>"
        f"<td style='padding:10px 12px'>{last_date}</td>"
        f"<td style='padding:10px 12px;color:{dc};font-weight:500'>{days} days</td>"
        f"<td style='padding:10px 12px;color:{tc};font-weight:600'>{row['status']}</td>"
        f"<td style='padding:10px 12px'>{spend}</td>"
        f"</tr>"
    )

st.markdown(
    "<table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:4px'>"
    "<thead><tr style='border-bottom:2px solid #e5e7eb'>"
    + "".join(
        f"<th style='text-align:left;padding:8px 12px;font-size:11px;color:#6b7280;"
        f"text-transform:uppercase;letter-spacing:0.5px;font-weight:600'>{h}</th>"
        for h in ["Door Name", "City / State", "Rep", "Last Order Date",
                  "Days Since Order", "Status", "Monthly Spend"]
    )
    + f"</tr></thead><tbody>{rows_html}</tbody></table>",
    unsafe_allow_html=True,
)
