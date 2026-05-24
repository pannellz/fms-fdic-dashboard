"""
FMS FDIC Intelligence Dashboard
Run with:  streamlit run app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import fdic_data as fdic

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FMS FDIC Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Authentication gate ──────────────────────────────────────────────────────
def _check_password():
    """Return True if the user has entered a correct password."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Check if password protection is configured
    if "password" not in st.secrets:
        return True  # No password configured — allow access (local dev)

    st.markdown(
        "<div style='max-width:400px;margin:120px auto;text-align:center'>"
        "<h2 style='color:#2c373f'>🏦 FMS FDIC Dashboard</h2>"
        "<p style='color:#7c848a;font-size:14px'>Enter your team password to continue</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed")
        if st.button("Sign in", type="primary", use_container_width=True):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
    return False

if not _check_password():
    st.stop()

# ── Colour palette (FMS brand — thefmsagency.com) ────────────────────────────
C_NAVY   = "#2c373f"   # FMS primary dark slate
C_BLUE   = "#4a5860"   # FMS dark slate lighter
C_LTBLUE = "#95dae2"   # FMS teal
C_GREEN  = "#2a9d5c"   # Positive indicator (FMS-adjacent)
C_RED    = "#f0514b"   # FMS coral accent
C_AMBER  = "#f0514b"   # FMS coral (used for trend lines & highlights)
C_GREY   = "#7c848a"   # FMS muted grey
C_ALT    = "#ceeef2"   # FMS light teal (row highlights)
C_BORDER = "#d5d7d9"   # FMS border grey

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="'PP Mori', Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                  size=12, color=C_NAVY),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=40, b=40, l=60, r=20),
        colorway=[C_NAVY, C_LTBLUE, C_GREEN, C_RED, C_GREY, C_BLUE],
    )
)

# ── FMS brand CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global font override */
    html, body, [class*="css"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #2c373f;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #fff !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] small {
        color: rgba(255,255,255,0.7) !important;
    }
    /* Keep dropdown inputs readable — dark text on white background */
    [data-testid="stSidebar"] [data-baseweb="select"] {
        background-color: #fff;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #2c373f !important;
    }
    [data-testid="stSidebar"] input {
        color: #2c373f !important;
        background-color: #fff !important;
    }
    /* Sidebar button */
    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.25);
        color: #fff !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255,255,255,0.2);
        border-color: rgba(255,255,255,0.4);
    }
    /* Sidebar divider */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.15);
    }

    /* Header styling */
    h1, h2, h3 {
        font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 600;
        color: #2c373f;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #f8fafb;
        border: 1px solid #d5d7d9;
        border-radius: 8px;
        padding: 10px 12px;
    }
    [data-testid="stMetricLabel"] {
        color: #7c848a;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    [data-testid="stMetricLabel"] > div > div {
        font-size: 10px !important;
        white-space: nowrap;
        overflow: visible;
    }
    [data-testid="stMetricValue"] {
        color: #2c373f;
        font-weight: 600;
        font-size: 22px !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 11px !important;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #f0514b;
        border-color: #f0514b;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #d94440;
        border-color: #d94440;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom-color: #f0514b;
        color: #2c373f;
    }

    /* Divider */
    hr {
        border-color: #d5d7d9;
    }

    /* Dataframe header */
    [data-testid="stDataFrame"] th {
        background-color: #2c373f !important;
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Formatting helpers ─────────────────────────────────────────────────────────

def fmt_dep(val_thousands):
    """Format deposit/asset dollar amount from thousands."""
    if pd.isna(val_thousands):
        return "—"
    val = float(val_thousands)
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.2f}B"
    if abs(val) >= 1_000:
        return f"${val/1_000:.1f}M"
    return f"${val:.0f}K"


def fmt_pct(val, decimals=2):
    if pd.isna(val):
        return "—"
    return f"{float(val):.{decimals}f}%"


def delta_color(val):
    if pd.isna(val) or val == 0:
        return "off"
    return "normal" if val > 0 else "inverse"


def peer_median(peers_df, col):
    if peers_df.empty or col not in peers_df.columns:
        return None
    vals = pd.to_numeric(peers_df[col], errors="coerce").dropna()
    return float(vals.median()) if len(vals) > 0 else None


# ── Load client registry ───────────────────────────────────────────────────────
REGISTRY_PATH = Path(__file__).parent.parent / "FMS_Client_FDIC_Certs.xlsx"

@st.cache_data(ttl=300)
def load_registry():
    df = pd.read_excel(REGISTRY_PATH)
    df["FDIC Cert #"] = pd.to_numeric(df["FDIC Cert #"], errors="coerce")
    df = df.dropna(subset=["FDIC Cert #"])
    df["FDIC Cert #"] = df["FDIC Cert #"].astype(int)
    return df


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:#fff;margin-bottom:0'>FMS</h2>"
                "<p style='color:rgba(255,255,255,0.6);margin-top:0;font-size:13px'>"
                "FDIC Intelligence Dashboard</p>",
                unsafe_allow_html=True)
    st.divider()

    registry = load_registry()
    client_names = sorted(registry["Bank Name"].tolist())
    selected_name = st.selectbox("Select Client", client_names)

    row      = registry[registry["Bank Name"] == selected_name].iloc[0]
    cert     = int(row["FDIC Cert #"])
    launch_raw = row.get("Brand Launch Date", None)
    in_rebrand = str(row.get("Include in Rebrand Measurement Report?", "No")).strip().lower() == "yes"

    try:
        launch_year = int(launch_raw) if isinstance(launch_raw, (int, float)) and not pd.isna(launch_raw) \
                      else pd.Timestamp(launch_raw).year if pd.notna(launch_raw) else None
    except Exception:
        launch_year = None

    st.divider()

    # Cache status
    status = fdic.cache_status_all(cert)
    fin_ts = status.get("financials")
    if fin_ts:
        age   = (pd.Timestamp.now() - pd.Timestamp(fin_ts)).days
        color = C_GREEN if age < 90 else C_AMBER
        st.markdown(f"<small style='color:{color}'>● Data refreshed {age}d ago</small>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<small style='color:{C_GREY}'>● No cached data</small>",
                    unsafe_allow_html=True)

    refresh = st.button("↻  Refresh This Client", use_container_width=True)
    st.caption(f"FDIC Cert: {cert}")
    if launch_year:
        st.caption(f"Brand launch: {launch_year}")
    if in_rebrand:
        st.caption("✓ In rebrand analysis")


# ── Load data ─────────────────────────────────────────────────────────────────
if refresh or not fdic.is_fresh(cert, "financials"):
    status_box = st.empty()
    def update_status(msg):
        status_box.info(f"⏳ {msg}")

    with st.spinner("Loading FDIC data…"):
        data = fdic.load_client_data(cert, force_refresh=refresh, on_status=update_status)
    status_box.empty()
else:
    data = fdic.load_client_data(cert, force_refresh=False)

inst       = data.get("institution",  pd.DataFrame())
financials = data.get("financials",   pd.DataFrame())
sod        = data.get("sod",          pd.DataFrame())
locations  = data.get("locations",    pd.DataFrame())
history    = data.get("history",      pd.DataFrame())
peers      = data.get("peers",        pd.DataFrame())
market_sod = data.get("market_sod",   pd.DataFrame())

if inst.empty:
    st.error("Could not load institution data. Try refreshing.")
    st.stop()

# Convenience: pull scalar institution values
inst_row     = inst.iloc[0]
inst_name    = inst_row.get("NAME", selected_name)
inst_city    = inst_row.get("CITY", "")
inst_state   = inst_row.get("STALP", "")
inst_assets  = float(inst_row.get("ASSET", 0) or 0)
inst_cbsa    = inst_row.get("CBSA", "")
_raw_est     = str(inst_row.get("ESTYMD", "")) if inst_row.get("ESTYMD") else ""
try:
    inst_est = str(pd.to_datetime(_raw_est).year) if _raw_est else ""
except Exception:
    inst_est = _raw_est[-4:] if len(_raw_est) >= 4 else _raw_est
inst_web     = inst_row.get("WEBADDR", "")
inst_hc      = inst_row.get("NAMEHCR", "")
inst_mdi     = inst_row.get("MDI_STATUS_DESC", "")


# ── Page header ────────────────────────────────────────────────────────────────
col_title, col_meta = st.columns([3, 2])
with col_title:
    st.markdown(f"<h1 style='color:{C_NAVY};margin-bottom:4px'>{inst_name}</h1>",
                unsafe_allow_html=True)
    meta_parts = [f"{inst_city}, {inst_state}"]
    if inst_est:
        meta_parts.append(f"Est. {inst_est}")
    if inst_cbsa:
        meta_parts.append(inst_cbsa)
    st.caption("  •  ".join(meta_parts))

with col_meta:
    if inst_hc:
        st.caption(f"Holding company: {inst_hc}")
    if inst_mdi and inst_mdi.upper() != "NONE":
        st.caption(f"MDI: {inst_mdi}")
    if inst_web:
        st.caption(f"[{inst_web}](https://{inst_web})")

st.divider()

# ── KPI snapshot bar ──────────────────────────────────────────────────────────
def latest_fin(col):
    if financials.empty or col not in financials.columns:
        return None, None
    fin = financials.sort_values("date").dropna(subset=[col])
    if fin.empty:
        return None, None
    cur = float(fin[col].iloc[-1])
    prev = float(fin[col].iloc[-2]) if len(fin) >= 2 else None
    delta = (cur - prev) if prev is not None else None
    return cur, delta

def latest_sod_share():
    """Market share across ALL counties — used for the headline KPI.
    Numerator and denominator both use market_sod (branch-level, same scope)."""
    if market_sod.empty:
        return None, None
    years = sorted(market_sod["YEAR"].dropna().astype(int).unique())
    if len(years) < 1:
        return None, None
    cur_yr  = years[-1]
    prev_yr = years[-2] if len(years) >= 2 else None

    cur_mkt  = market_sod[market_sod["YEAR"] == cur_yr]
    cert_dep = cur_mkt[cur_mkt["CERT"] == cert]["DEPSUMBR"].sum()
    mkt_dep  = cur_mkt["DEPSUMBR"].sum()
    if not cert_dep or not mkt_dep:
        return None, None
    share = cert_dep / mkt_dep * 100

    prev_share = None
    if prev_yr:
        prev_mkt = market_sod[market_sod["YEAR"] == prev_yr]
        pd_c = prev_mkt[prev_mkt["CERT"] == cert]["DEPSUMBR"].sum()
        pd_m = prev_mkt["DEPSUMBR"].sum()
        if pd_c and pd_m:
            prev_share = pd_c / pd_m * 100
    delta = (share - prev_share) if prev_share else None
    return share, delta

roa, roa_d         = latest_fin("ROA")
roe, roe_d         = latest_fin("ROE")
nim, nim_d         = latest_fin("NIMY")
eff, eff_d         = latest_fin("EEFFR")
loans, loans_d     = latest_fin("LNLSNET")
share, share_d     = latest_sod_share()

# Use whichever source has the most recent deposit figure
_sod_dep = float(sod[sod["YEAR"] == sod["YEAR"].max()]["DEPDOM"].iloc[0]) if not sod.empty else 0
_fin_dep = float(financials.sort_values("date").iloc[-1]["DEP"]) \
           if not financials.empty and "DEP" in financials.columns else 0
cur_dep = max(_sod_dep, _fin_dep) if (_sod_dep or _fin_dep) else inst_assets

k0, k1, k2, k3, k4, k5, k6 = st.columns(7)
k0.metric("Assets",           fmt_dep(inst_assets))
k1.metric("Deposits",         fmt_dep(cur_dep))
k2.metric("Mkt Share",        fmt_pct(share, 1) if share else "—",
          f"{share_d:+.2f}pp" if share_d else None,
          delta_color(share_d) if share_d else "off")
k3.metric("Net Loans",        fmt_dep(loans),
          fmt_dep(loans_d) if loans_d else None,
          delta_color="off")
k4.metric("ROA",              fmt_pct(roa) if roa else "—",
          f"{roa_d:+.2f}%" if roa_d else None,
          delta_color(roa_d) if roa_d else "off")
k5.metric("NIM",              fmt_pct(nim) if nim else "—",
          f"{nim_d:+.2f}%" if nim_d else None,
          delta_color(nim_d) if nim_d else "off")
k6.metric("Efficiency",       fmt_pct(eff) if eff else "—",
          f"{eff_d:+.2f}%" if eff_d else None,
          delta_color="off")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_mkt, tab_growth, tab_health, tab_foot, tab_rebrand, tab_insights = st.tabs([
    "📊 Market Position",
    "📈 Deposit & Loan Growth",
    "🏥 Financial Health",
    "🗺️ Branch & Staffing",
    "🎯 Rebrand Timeline",
    "💡 AI Insights",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MARKET POSITION
# ══════════════════════════════════════════════════════════════════════════════
with tab_mkt:
    if sod.empty:
        st.info("No SOD data available.")
    elif market_sod.empty:
        st.info("No market data available.")
    else:
        years     = sorted(sod["YEAR"].dropna().astype(int).unique())
        latest_yr = max(years)
        name_col  = "NAMEFULL" if "NAMEFULL" in market_sod.columns else "CERT"

        # ── County selector ───────────────────────────────────────────────────
        all_counties = sorted(market_sod["CNTYNAMB"].dropna().unique().tolist())
        sel_counties = st.multiselect(
            "Filter by County",
            options=all_counties,
            default=all_counties,
            help="Select one or more counties to focus the market analysis. Default shows all counties.",
        )
        if not sel_counties:
            sel_counties = all_counties

        mkt = market_sod[market_sod["CNTYNAMB"].isin(sel_counties)]
        mkt_latest = mkt[mkt["YEAR"] == latest_yr]

        # ── County breakdown table ────────────────────────────────────────────
        st.subheader(f"Market Share by County  —  {latest_yr}")
        st.caption("Client branch deposits ÷ total branch deposits in each county · FDIC Summary of Deposits")

        cnty_rows = []
        for county in sorted(sel_counties):
            cnty_data  = mkt_latest[mkt_latest["CNTYNAMB"] == county]
            if cnty_data.empty:
                continue
            total_dep  = cnty_data["DEPSUMBR"].sum()
            client_dep = cnty_data[cnty_data["CERT"] == cert]["DEPSUMBR"].sum()
            if total_dep == 0:
                continue
            by_bank = cnty_data.groupby("CERT")["DEPSUMBR"].sum().sort_values(ascending=False)
            rank    = int((by_bank > client_dep).sum()) + 1
            cnty_rows.append({
                "County":               county,
                "Client Deposits":      client_dep,
                "Market Total":         total_dep,
                "Market Share (%)":     round(client_dep / total_dep * 100, 2),
                "Rank":                 f"{rank} of {len(by_bank)}",
            })

        if cnty_rows:
            cnty_df = pd.DataFrame(cnty_rows).sort_values("Market Share (%)", ascending=False)
            cnty_col_config = {
                "Client Deposits": st.column_config.NumberColumn(
                    "Client Deposits (in thousands)", format="$%,.0f"),
                "Market Total": st.column_config.NumberColumn(
                    "Market Total (in thousands)", format="$%,.0f"),
                "Market Share (%)": st.column_config.NumberColumn(
                    "Market Share (%)", format="%.2f%%"),
            }
            st.dataframe(cnty_df, use_container_width=True, hide_index=True,
                         column_config=cnty_col_config)

        st.divider()

        # ── Market share trend ────────────────────────────────────────────────
        if sel_counties == all_counties:
            scope_label = f"All {len(all_counties)} Counties"
        elif len(sel_counties) <= 4:
            scope_label = ", ".join(sel_counties)
        else:
            scope_label = f"{len(sel_counties)} Selected Counties"
        st.subheader("Deposit Market Share Trend")
        st.caption(f"Client branch deposits ÷ total market deposits · {scope_label}")

        trend_rows = []
        for yr in years:
            yr_mkt = mkt[mkt["YEAR"] == yr]
            c_dep  = yr_mkt[yr_mkt["CERT"] == cert]["DEPSUMBR"].sum()
            m_dep  = yr_mkt["DEPSUMBR"].sum()
            if m_dep:
                trend_rows.append({
                    "Year":                  yr,
                    "Client Deposits ($K)":  float(c_dep),
                    "Market Total ($K)":     float(m_dep),
                    "Market Share (%)":      c_dep / m_dep * 100,
                })
        share_df = pd.DataFrame(trend_rows)

        if not share_df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=share_df["Year"],
                y=share_df["Client Deposits ($K)"] / 1000,
                name=f"{inst_name} Deposits ($M)", marker_color=C_NAVY,
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=share_df["Year"], y=share_df["Market Share (%)"],
                name="Market Share %", mode="lines+markers",
                line=dict(color=C_AMBER, width=3),
                marker=dict(size=8),
            ), secondary_y=True)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              legend=dict(orientation="h", y=-0.15))
            fig.update_yaxes(title_text=f"{inst_name} Deposits ($M)",
                             secondary_y=False)
            fig.update_yaxes(title_text="Market Share (%)", secondary_y=True,
                             ticksuffix="%", showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ── Competitor table ───────────────────────────────────────────────────
        n_scope = "All Markets" if sel_counties == all_counties else f"{len(sel_counties)} Selected Counties"
        st.subheader(f"Competitors — {n_scope}  ({latest_yr})")

        comp = (mkt_latest
                .groupby(["CERT", name_col])["DEPSUMBR"]
                .sum()
                .reset_index()
                .sort_values("DEPSUMBR", ascending=False))
        total_mkt = comp["DEPSUMBR"].sum()
        comp["Market Share"] = (comp["DEPSUMBR"] / total_mkt * 100).round(2)
        comp["Deposits ($M)"] = (comp["DEPSUMBR"] / 1000).round(1)
        comp["Rank"] = range(1, len(comp) + 1)
        comp["Institution"] = comp[name_col].astype(str)

        display = comp[["Rank", "Institution", "Deposits ($M)", "Market Share"]].copy()

        def highlight_client(row):
            match = comp[comp["Rank"] == row["Rank"]]["CERT"].astype(str).values
            if len(match) and match[0] == str(cert):
                return [f"background-color: {C_ALT}; font-weight: bold"] * len(row)
            return [""] * len(row)

        comp_col_config = {
            "Deposits ($M)": st.column_config.NumberColumn(
                "Deposits ($M)", format="$%,.1f"),
            "Market Share": st.column_config.NumberColumn(
                "Market Share (%)", format="%.2f%%"),
        }
        st.dataframe(
            display.style.apply(highlight_client, axis=1),
            use_container_width=True, hide_index=True,
            column_config=comp_col_config,
        )
        st.caption(
            f"Data: {latest_yr} FDIC Summary of Deposits  |  "
            f"{len(sel_counties)} {'county' if len(sel_counties) == 1 else 'counties'} included  |  "
            f"{len(comp)} institutions"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEPOSIT & LOAN GROWTH
# ══════════════════════════════════════════════════════════════════════════════
with tab_growth:
    col_l, col_r = st.columns(2)

    # ── Deposits (annual SOD) ─────────────────────────────────────────────────
    with col_l:
        st.subheader("Total Deposits")
        st.caption("Annual, as of June 30 (FDIC Summary of Deposits)")
        if not sod.empty:
            dep_annual = (sod.groupby("YEAR")["DEPDOM"]
                          .first()
                          .reset_index()
                          .sort_values("YEAR"))
            dep_annual["Deposits ($M)"] = dep_annual["DEPDOM"] / 1000
            dep_annual["YoY %"] = dep_annual["Deposits ($M)"].pct_change() * 100

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=dep_annual["YEAR"], y=dep_annual["Deposits ($M)"],
                name="Deposits ($M)", marker_color=C_NAVY,
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=dep_annual["YEAR"], y=dep_annual["YoY %"],
                name="YoY Growth %", mode="lines+markers",
                line=dict(color=C_AMBER, width=2),
            ), secondary_y=True)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"])
            fig.update_yaxes(title_text="Deposits ($M)", secondary_y=False)
            fig.update_yaxes(title_text="YoY Growth (%)", secondary_y=True,
                             ticksuffix="%", showgrid=False)
            st.plotly_chart(fig, use_container_width=True)

            # Core vs total
            if not financials.empty and "COREDEP" in financials.columns:
                st.caption("Core vs. Total Deposits (quarterly)")
                q4 = financials[financials["quarter"] == 4].copy()
                if not q4.empty:
                    q4["Total Dep ($M)"]  = q4["DEP"]    / 1000
                    q4["Core Dep ($M)"]   = q4["COREDEP"] / 1000
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=q4["date"], y=q4["Total Dep ($M)"],
                                              name="Total", line=dict(color=C_NAVY)))
                    fig2.add_trace(go.Scatter(x=q4["date"], y=q4["Core Dep ($M)"],
                                              name="Core", line=dict(color=C_LTBLUE, dash="dot")))
                    fig2.update_layout(**PLOTLY_TEMPLATE["layout"],
                                       legend=dict(orientation="h", y=-0.2))
                    st.plotly_chart(fig2, use_container_width=True)

    # ── Loans (quarterly) ────────────────────────────────────────────────────
    with col_r:
        st.subheader("Net Loans & Leases")
        st.caption("Quarterly Call Report data")
        if not financials.empty and "LNLSNET" in financials.columns:
            fin = financials.dropna(subset=["LNLSNET"]).copy()
            fin["Loans ($M)"] = fin["LNLSNET"] / 1000
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=fin["date"], y=fin["Loans ($M)"],
                fill="tozeroy", fillcolor=f"rgba(31,56,100,0.1)",
                line=dict(color=C_NAVY, width=2), name="Net Loans ($M)",
            ))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"])
            st.plotly_chart(fig, use_container_width=True)

            # Loan-to-deposit ratio
            if "DEP" in financials.columns:
                st.caption("Loan-to-Deposit Ratio (quarterly)")
                fin2 = financials.dropna(subset=["LNLSNET", "DEP"]).copy()
                fin2["L/D Ratio (%)"] = fin2["LNLSNET"] / fin2["DEP"] * 100
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=fin2["date"], y=fin2["L/D Ratio (%)"],
                    line=dict(color=C_LTBLUE, width=2), name="L/D Ratio",
                ))
                fig3.add_hline(y=80, line_dash="dot", line_color=C_AMBER,
                               annotation_text="80% guideline")
                fig3.update_layout(**PLOTLY_TEMPLATE["layout"],
                                   yaxis_ticksuffix="%")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Loan data not available.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FINANCIAL HEALTH
# ══════════════════════════════════════════════════════════════════════════════
with tab_health:
    if financials.empty:
        st.info("No financial data available.")
    else:
        fin = financials.sort_values("date").copy()

        p_roa  = peer_median(peers, "ROA")
        p_roe  = peer_median(peers, "ROE")
        p_nim  = peer_median(peers, "NIMY")
        p_eff  = peer_median(peers, "EEFFR")

        def ratio_chart(col, title, peer_val, good_direction="up",
                        benchmark=None, benchmark_label=None, suffix="%"):
            sub = fin.dropna(subset=[col]).copy()
            if sub.empty:
                st.caption(f"{title}: no data")
                return
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sub["date"], y=sub[col],
                name=title, line=dict(color=C_NAVY, width=2),
                fill="tozeroy", fillcolor=f"rgba(31,56,100,0.07)",
            ))
            if peer_val is not None:
                fig.add_hline(y=peer_val, line_dash="dash", line_color=C_GREY,
                               annotation_text=f"Peer median: {peer_val:.2f}{suffix}",
                               annotation_position="top left")
            if benchmark is not None:
                fig.add_hline(y=benchmark, line_dash="dot", line_color=C_AMBER,
                               annotation_text=benchmark_label or str(benchmark),
                               annotation_position="bottom left")
            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              title=dict(text=title, font=dict(color=C_NAVY)),
                              yaxis_ticksuffix=suffix, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Profitability")
        st.caption(
            "**ROA** measures how efficiently the bank turns assets into profit — "
            "above 1.0% is the community bank benchmark, and higher is better. "
            "**ROE** measures the return generated on shareholder equity — "
            "10%+ is generally considered strong. "
            "**Net Interest Margin (NIM)** is the spread between what the bank earns on loans "
            "and what it pays on deposits — a wider margin means more income from core lending. "
            "**Efficiency Ratio** shows how many cents it costs to generate a dollar of revenue — "
            "lower is better, and above 70% is a caution flag."
        )
        c1, c2 = st.columns(2)
        with c1:
            ratio_chart("ROA",  "Return on Assets (ROA)",  p_roa,
                        benchmark=1.0, benchmark_label="1.0% community bank benchmark")
            ratio_chart("NIMY", "Net Interest Margin",     p_nim)
        with c2:
            ratio_chart("ROE",  "Return on Equity (ROE)",  p_roe)
            ratio_chart("EEFFR","Efficiency Ratio",        p_eff,
                        good_direction="down",
                        benchmark=70, benchmark_label="70% caution threshold")

        st.divider()
        st.subheader("Asset Quality")
        st.caption(
            "**Non-Performing Loan (NPL) Ratio** is the percentage of loans that are 90+ days "
            "past due or in non-accrual status — above 1.0% raises regulatory concern. "
            "**Net Charge-Off Ratio** is the percentage of loans the bank has written off as losses "
            "(net of recoveries) — lower is better, and a rising trend can signal deteriorating "
            "credit quality in the loan portfolio."
        )
        c3, c4 = st.columns(2)
        with c3:
            ratio_chart("NTLNLSR", "Non-Performing Loan Ratio", None,
                        benchmark=1.0, benchmark_label="1.0% industry watch level")
        with c4:
            ratio_chart("NCLNLSR", "Net Charge-Off Ratio", None)

        st.divider()
        st.subheader("Capital Strength")

        # Detect CBLR election: IDT1RWAJR goes to 0 when bank opts into
        # Community Bank Leverage Ratio framework (available since Q1 2020)
        _cblr_elected = False
        if not financials.empty and "IDT1RWAJR" in financials.columns:
            recent_t1rwa = financials.sort_values("date").tail(4)["IDT1RWAJR"]
            _cblr_elected = (recent_t1rwa == 0).all()

        if _cblr_elected:
            st.caption(
                "**Tier 1 Leverage Ratio** compares the bank's core equity to total assets — "
                "5%+ is the well-capitalized threshold and 9%+ qualifies for the simplified "
                "Community Bank Leverage Ratio (CBLR) framework. "
                "This bank has elected the **CBLR framework** (available since 2020), so it no longer "
                "reports risk-based capital ratios. Under CBLR, a leverage ratio above 9% is "
                "considered well-capitalized for all regulatory purposes."
            )
            ratio_chart("RBC1AAJ", "Tier 1 Leverage Ratio (CBLR)", None,
                        benchmark=9.0, benchmark_label="9.0% CBLR well-capitalized threshold")
        else:
            st.caption(
                "**Tier 1 Leverage Ratio** is core equity divided by total assets — "
                "5%+ is the well-capitalized threshold. "
                "**Tier 1 Risk-Based Capital Ratio** compares core equity to risk-weighted assets — "
                "regulators require at least 6%, and 8%+ is considered well-capitalized. "
                "Both ratios indicate how much cushion the bank has to absorb losses."
            )
            c5, c6 = st.columns(2)
            with c5:
                ratio_chart("RBC1AAJ", "Tier 1 Leverage Ratio", None,
                            benchmark=5.0, benchmark_label="5.0% well-capitalized minimum")
            with c6:
                ratio_chart("IDT1RWAJR", "Tier 1 Risk-Based Capital Ratio", None,
                            benchmark=8.0, benchmark_label="8.0% well-capitalized minimum")

        if not peers.empty:
            st.divider()
            scope = peers["Peer Scope"].iloc[0] if "Peer Scope" in peers.columns else "Market"
            st.subheader(f"Peer Benchmarking  —  {len(peers)} comparable institutions ({scope})")
            st.caption("Current snapshot · Similar asset size (0.25×–4× client)")
            # Only show columns that actually exist
            peer_cols   = ["NAME", "CITY", "STALP", "ASSET", "ROA", "ROE", "OFFICES"]
            peer_labels = ["Institution", "City", "State", "Assets (in thousands)", "ROA %", "ROE %", "Branches"]
            p_disp = peers[[c for c in peer_cols if c in peers.columns]].copy()
            p_disp.columns = peer_labels[:len(p_disp.columns)]
            p_disp = p_disp.sort_values("Assets (in thousands)", ascending=False)
            col_config = {
                "Assets (in thousands)": st.column_config.NumberColumn(
                    "Assets (in thousands)", format="$%,.0f"),
                "ROA %":    st.column_config.NumberColumn("ROA %",    format="%.2f%%"),
                "ROE %":    st.column_config.NumberColumn("ROE %",    format="%.2f%%"),
                "Branches": st.column_config.NumberColumn("Branches", format="%d"),
            }
            st.dataframe(p_disp, use_container_width=True, hide_index=True,
                         column_config=col_config)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BRANCH & STAFFING
# ══════════════════════════════════════════════════════════════════════════════
with tab_foot:
    # ── Row 1: Map (full width) ──────────────────────────────────────────────
    st.subheader("Branch Locations")
    if not locations.empty and "LATITUDE" in locations.columns:
        loc = locations.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
        if not loc.empty:
            loc["Type"] = loc.get("SERVTYPE_DESC", "Branch").fillna("Branch")
            loc["label"] = loc.apply(
                lambda r: f"{r.get('OFFNAME','Branch')} — {r.get('CITY','')}", axis=1)
            # Compute zoom level based on geographic spread of branches
            _lat_span = loc["LATITUDE"].max() - loc["LATITUDE"].min()
            _lon_span = loc["LONGITUDE"].max() - loc["LONGITUDE"].min()
            _span = max(_lat_span, _lon_span, 0.01)
            if _span > 4:
                _zoom = 5
            elif _span > 2:
                _zoom = 6
            elif _span > 1:
                _zoom = 7
            elif _span > 0.5:
                _zoom = 8
            else:
                _zoom = 9
            fig = px.scatter_mapbox(
                loc, lat="LATITUDE", lon="LONGITUDE",
                hover_name="label", hover_data={"LATITUDE": False, "LONGITUDE": False,
                                                 "COUNTY": True, "ZIP": True},
                color_discrete_sequence=[C_NAVY],
                zoom=_zoom, height=500,
            )
            fig.update_layout(mapbox_style="open-street-map",
                              margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"{len(loc)} branch locations")
    else:
        st.info("Location data not available.")

    st.divider()

    # ── Row 2: Branch count + Employees side by side ─────────────────────────
    col_br, col_emp = st.columns(2)

    with col_br:
        st.subheader("Branch Count Over Time")
        if not sod.empty:
            branch_ct = (sod.groupby("YEAR")
                         .size()
                         .reset_index(name="Branches")
                         .sort_values("YEAR"))
            fig = go.Figure(go.Scatter(
                x=branch_ct["YEAR"], y=branch_ct["Branches"],
                mode="lines+markers", line=dict(color=C_NAVY, width=2),
                marker=dict(size=7),
            ))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              yaxis_title="Branch Count")
            st.plotly_chart(fig, use_container_width=True)

    with col_emp:
        st.subheader("Employees")
        if not financials.empty and "NUMEMP" in financials.columns:
            emp = financials.dropna(subset=["NUMEMP"]).copy()
            emp = emp[emp["quarter"] == 4]   # year-end snapshots
            fig2 = go.Figure(go.Bar(
                x=emp["year"], y=emp["NUMEMP"],
                marker_color=C_LTBLUE,
            ))
            fig2.update_layout(**PLOTLY_TEMPLATE["layout"],
                               yaxis_title="Full-Time Equivalent Employees")
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Row 3: Key events (full width) ───────────────────────────────────────
    if not history.empty:
        st.subheader("Key Events")
        _event_codes = ["711", "712", "713", "721", "722", "810", "811", "520"]
        events = history[history["CHANGECODE"].astype(str).isin(_event_codes)].copy()
        label_map = {
            "711": "Branch Opening",    "712": "Branch Purchased",
            "713": "Branch Acquired",   "721": "Branch Closing",
            "722": "Branch Sold",       "810": "Merger / Consolidation",
            "811": "Merger / Consolidation", "520": "Location Change",
        }
        events["Event"] = events["CHANGECODE"].astype(str).map(label_map)
        def _fmt_location(r):
            name = str(r.get("OFF_NAME", "")) if pd.notna(r.get("OFF_NAME")) else ""
            city = str(r.get("OFF_PCITY", "")) if pd.notna(r.get("OFF_PCITY")) else ""
            if name and city:
                return f"{name} — {city}"
            return name or city or "—"
        events["Location"] = events.apply(_fmt_location, axis=1)
        ev_disp = events[["EFFDATE", "Event", "Location"]].tail(50)
        ev_disp.columns = ["Effective Date", "Event", "Location"]
        ev_disp["Effective Date"] = pd.to_datetime(
            ev_disp["Effective Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(ev_disp.sort_values("Effective Date", ascending=False),
                     use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — REBRAND TIMELINE
# ══════════════════════════════════════════════════════════════════════════════
with tab_rebrand:
    if not launch_year:
        st.info(f"No brand launch date is recorded for {selected_name}. "
                "Add one to the client registry to unlock this view.")
    elif not in_rebrand:
        st.info(f"{selected_name} is not included in the rebrand analysis "
                "(see 'Include in Rebrand Measurement Report?' column in the registry).")
    else:
        st.subheader(f"Before / After Rebrand  —  Launch Year: {launch_year}")
        st.caption(
            "This tab compares deposit growth before and after the brand launch to help "
            "gauge whether the rebrand coincided with a change in momentum. "
            "The left chart shows total deposits each year, with green bars for post-launch. "
            "The right chart indexes everything to the launch year (launch = 100) so you "
            "can see relative growth at a glance."
        )

        if not sod.empty:
            dep = (sod.groupby("YEAR")["DEPDOM"]
                   .first()
                   .reset_index()
                   .sort_values("YEAR"))
            dep["Years from Launch"] = dep["YEAR"] - launch_year
            dep["Deposits ($M)"] = dep["DEPDOM"] / 1000

            # Index deposits to launch year = 100
            base = dep[dep["YEAR"] == launch_year]["Deposits ($M)"]
            if not base.empty:
                base_val = float(base.iloc[0])
                dep["Indexed (Launch=100)"] = dep["Deposits ($M)"] / base_val * 100

                # ── Snapshot metrics ─────────────────────────────────────────
                pre  = dep[dep["Years from Launch"] < 0]
                post = dep[dep["Years from Launch"] >= 0]
                launch_dep = base_val
                latest_dep = float(dep.iloc[-1]["Deposits ($M)"])
                earliest_dep = float(dep.iloc[0]["Deposits ($M)"])

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Deposits at Launch", f"${launch_dep:,.0f}M")
                m2.metric("Most Recent", f"${latest_dep:,.0f}M")
                growth_pct = (latest_dep - launch_dep) / launch_dep * 100 if launch_dep else 0
                growth_dol = latest_dep - launch_dep
                m3.metric("Growth Since Launch",
                          f"${growth_dol:+,.0f}M",
                          f"{growth_pct:+.1f}%",
                          delta_color=delta_color(growth_dol))
                yrs_since = int(dep.iloc[-1]["YEAR"]) - launch_year
                if yrs_since > 0:
                    m4.metric("Avg. Annual Growth (Post)",
                              f"${growth_dol / yrs_since:,.0f}M/yr")
                else:
                    m4.metric("Years Since Launch", "< 1 year")

                st.divider()

                # ── Charts ───────────────────────────────────────────────────
                col_a, col_b = st.columns(2)
                with col_a:
                    fig = go.Figure()
                    fig.add_vrect(x0=-0.5, x1=dep["Years from Launch"].max() + 0.5,
                                  fillcolor=f"rgba(33,115,70,0.05)", layer="below",
                                  line_width=0, annotation_text="Post-launch",
                                  annotation_position="top left")
                    fig.add_trace(go.Bar(
                        x=dep["Years from Launch"], y=dep["Deposits ($M)"],
                        marker_color=[C_GREEN if y >= 0 else C_NAVY
                                       for y in dep["Years from Launch"]],
                        name="Deposits ($M)",
                    ))
                    fig.add_vline(x=0, line_dash="dash", line_color=C_RED,
                                  annotation_text=f"Launch ({launch_year})")
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                      xaxis_title="Years from Launch",
                                      yaxis_title="Deposits ($M)")
                    st.plotly_chart(fig, use_container_width=True)

                with col_b:
                    fig2 = go.Figure()
                    fig2.add_hline(y=100, line_dash="dot", line_color=C_GREY,
                                   annotation_text="Launch baseline")
                    fig2.add_trace(go.Scatter(
                        x=dep["Years from Launch"], y=dep["Indexed (Launch=100)"],
                        mode="lines+markers", line=dict(color=C_NAVY, width=2),
                        name="Indexed Deposits",
                    ))
                    fig2.add_vline(x=0, line_dash="dash", line_color=C_RED)
                    fig2.update_layout(**PLOTLY_TEMPLATE["layout"],
                                       xaxis_title="Years from Launch",
                                       yaxis_title="Deposits (Launch Year = 100)")
                    st.plotly_chart(fig2, use_container_width=True)

                # ── Before vs. After comparison ──────────────────────────────
                if len(pre) >= 2 and len(post) >= 2:
                    st.divider()
                    st.subheader("Growth Pace: Before vs. After")
                    st.caption(
                        "Compares average annual deposit growth in the years before the rebrand "
                        "to the years after. A positive change suggests deposits grew faster "
                        "after the brand launch."
                    )

                    pre_yrs  = int(pre.iloc[-1]["YEAR"]) - int(pre.iloc[0]["YEAR"])
                    post_yrs = int(post.iloc[-1]["YEAR"]) - int(post.iloc[0]["YEAR"])

                    pre_total  = float(pre.iloc[-1]["Deposits ($M)"] - pre.iloc[0]["Deposits ($M)"])
                    post_total = float(post.iloc[-1]["Deposits ($M)"] - post.iloc[0]["Deposits ($M)"])

                    pre_avg  = pre_total / pre_yrs if pre_yrs else 0
                    post_avg = post_total / post_yrs if post_yrs else 0
                    diff_avg = post_avg - pre_avg

                    pre_pct  = (pre.iloc[-1]["Deposits ($M)"] / pre.iloc[0]["Deposits ($M)"] - 1) * 100
                    post_pct = (post.iloc[-1]["Deposits ($M)"] / post.iloc[0]["Deposits ($M)"] - 1) * 100

                    g1, g2, g3 = st.columns(3)
                    g1.metric(
                        f"Before Rebrand ({int(pre.iloc[0]['YEAR'])}–{int(pre.iloc[-1]['YEAR'])})",
                        f"${pre_avg:,.0f}M / year",
                        f"{pre_pct:+.1f}% total over {pre_yrs} yrs",
                        delta_color="off",
                    )
                    g2.metric(
                        f"After Rebrand ({int(post.iloc[0]['YEAR'])}–{int(post.iloc[-1]['YEAR'])})",
                        f"${post_avg:,.0f}M / year",
                        f"{post_pct:+.1f}% total over {post_yrs} yrs",
                        delta_color="off",
                    )

                    if diff_avg >= 0:
                        verdict = "Deposit growth **accelerated** after the rebrand"
                        verdict_color = C_GREEN
                    else:
                        verdict = "Deposit growth **slowed** after the rebrand"
                        verdict_color = C_RED
                    g3.metric("Change in Pace", f"${diff_avg:+,.0f}M / year")
                    st.markdown(
                        f"<p style='font-size:16px; color:{verdict_color}; "
                        f"margin-top:8px'>{verdict}</p>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "Note: Many factors affect deposit growth — branch openings/closings, "
                        "acquisitions, rate environment, and local economic conditions all play a role. "
                        "This comparison shows correlation with the rebrand timing, not causation."
                    )

            # ── Multi-metric scorecard ────────────────────────────────────────
            st.divider()
            st.subheader("Full Rebrand Scorecard")
            st.caption(
                "A broader view of bank performance before and after the brand launch. "
                "Each metric compares the year-end value closest to launch against the most "
                "recent value. Green = improved, red = declined (accounting for direction — "
                "e.g. a lower efficiency ratio counts as an improvement)."
            )

            # Get year-end (Q4) financials closest to launch and most recent
            if not financials.empty:
                q4 = financials[financials["quarter"] == 4].sort_values("year").copy()
                pre_q4  = q4[q4["year"] < launch_year]
                post_q4 = q4[q4["year"] >= launch_year]
                launch_q4 = pre_q4.iloc[-1] if not pre_q4.empty else (
                    post_q4.iloc[0] if not post_q4.empty else None)
                latest_q4 = post_q4.iloc[-1] if not post_q4.empty else None

                # Branch count from SOD
                sod_at_launch = sod[sod["YEAR"] == launch_year]
                sod_latest    = sod[sod["YEAR"] == sod["YEAR"].max()]
                branches_launch = len(sod_at_launch) if not sod_at_launch.empty else None
                branches_latest = len(sod_latest) if not sod_latest.empty else None

                # Market share from market_sod
                def _mkt_share_yr(yr):
                    if market_sod.empty:
                        return None
                    yr_data = market_sod[market_sod["YEAR"] == yr]
                    if yr_data.empty:
                        return None
                    c = yr_data[yr_data["CERT"] == cert]["DEPSUMBR"].sum()
                    t = yr_data["DEPSUMBR"].sum()
                    return (c / t * 100) if t else None

                share_launch = _mkt_share_yr(launch_year)
                share_latest = _mkt_share_yr(int(sod["YEAR"].max()))

                if launch_q4 is not None and latest_q4 is not None:
                    # Build scorecard rows
                    # (label, at_launch, most_recent, format_fn, higher_is_better)
                    scorecard = []

                    def _add(label, col, fmt, higher_good=True):
                        lv = launch_q4.get(col)
                        rv = latest_q4.get(col)
                        if pd.notna(lv) and pd.notna(rv):
                            scorecard.append((label, float(lv), float(rv), fmt, higher_good))

                    _add("Total Assets",       "ASSET",    lambda x: fmt_dep(x), True)
                    _add("Total Deposits",     "DEP",      lambda x: fmt_dep(x), True)
                    _add("Net Loans",          "LNLSNET",  lambda x: fmt_dep(x), True)
                    _add("Net Income",         "NETINC",   lambda x: fmt_dep(x), True)
                    _add("Return on Assets",   "ROA",      lambda x: f"{x:.2f}%", True)
                    _add("Return on Equity",   "ROE",      lambda x: f"{x:.2f}%", True)
                    _add("Net Interest Margin","NIMY",     lambda x: f"{x:.2f}%", True)
                    _add("Efficiency Ratio",   "EEFFR",    lambda x: f"{x:.2f}%", False)
                    _add("Employees",          "NUMEMP",   lambda x: f"{int(x):,}", True)

                    if branches_launch is not None and branches_latest is not None:
                        scorecard.append(("Branches", branches_launch, branches_latest,
                                          lambda x: str(int(x)), True))

                    if share_launch is not None and share_latest is not None:
                        scorecard.append(("Market Share", share_launch, share_latest,
                                          lambda x: f"{x:.2f}%", True))

                    if scorecard:
                        launch_yr_label = int(launch_q4["year"]) if "year" in launch_q4.index else launch_year
                        latest_yr_label = int(latest_q4["year"]) if "year" in latest_q4.index else "Latest"

                        rows_out = []
                        for label, lv, rv, fmt_fn, higher_good in scorecard:
                            change = rv - lv
                            if lv != 0:
                                pct = (rv / lv - 1) * 100
                                pct_str = f"{pct:+.1f}%"
                            else:
                                pct_str = "—"
                            improved = (change > 0) if higher_good else (change < 0)
                            signal = "Improved" if improved else ("Declined" if change != 0 else "Flat")
                            rows_out.append({
                                "Metric":               label,
                                f"At Launch ({launch_yr_label})": fmt_fn(lv),
                                f"Most Recent ({latest_yr_label})": fmt_fn(rv),
                                "Change (%)":           pct_str,
                                "Trend":                signal,
                            })

                        sc_df = pd.DataFrame(rows_out)

                        def _color_trend(val):
                            if val == "Improved":
                                return f"color: {C_GREEN}; font-weight: bold"
                            elif val == "Declined":
                                return f"color: {C_RED}; font-weight: bold"
                            return ""

                        styled = sc_df.style.map(_color_trend, subset=["Trend"])
                        st.dataframe(styled, use_container_width=True, hide_index=True)

                        # Summary verdict
                        n_improved = sum(1 for r in rows_out if r["Trend"] == "Improved")
                        n_declined = sum(1 for r in rows_out if r["Trend"] == "Declined")
                        n_total    = len(rows_out)
                        st.markdown(
                            f"**{n_improved} of {n_total}** metrics improved since the "
                            f"brand launch, **{n_declined}** declined.",
                        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_insights:
    st.subheader("AI-Generated Narrative Insights")

    # Check for API key — env var takes precedence, then secrets.toml
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY") or None
        except Exception:
            api_key = None
    if api_key == "":
        api_key = None

    if not api_key:
        st.info(
            "**To enable AI insights**, paste your Anthropic API key into:\n\n"
            "`.streamlit/secrets.toml`  →  `ANTHROPIC_API_KEY = \"sk-ant-...\"`\n\n"
            "Get a key at **console.anthropic.com** → API Keys → Create Key. "
            "Then restart the dashboard — this tab will generate a plain-English analyst memo "
            "summarising the key trends, concerns, and opportunities visible in the data above."
        )
    else:
        import anthropic
        import hashlib

        # Load industry context if available
        _industry_ctx_path = Path(__file__).parent / "industry_context.md"
        _industry_ctx = ""
        if _industry_ctx_path.exists():
            _industry_ctx = _industry_ctx_path.read_text(encoding="utf-8")

        # Load client-specific context (pre-summarized Brand Discovery Report)
        _client_ctx = ""
        _client_ctx_dir = Path(__file__).parent / "ClientContext"
        if _client_ctx_dir.exists():
            import re as _re
            _safe_name = _re.sub(r'[^\w\s-]', '', inst_name.strip()).replace(" ", "_")
            _client_ctx_path = _client_ctx_dir / f"{_safe_name}.md"
            if _client_ctx_path.exists():
                _client_ctx = _client_ctx_path.read_text(encoding="utf-8")
            else:
                # Try matching with looser logic (ignore punctuation in filenames)
                for _f in _client_ctx_dir.glob("*.md"):
                    _f_clean = _re.sub(r'[^\w\s-]', '', _f.stem).lower()
                    if _f_clean == _safe_name.lower():
                        _client_ctx = _f.read_text(encoding="utf-8")
                        break

        # Show context availability
        ctx_sources = []
        if _industry_ctx:
            ctx_sources.append("industry benchmarks")
        if _client_ctx:
            ctx_sources.append("Brand Discovery Report")
        if ctx_sources:
            st.caption(f"✅ Enhanced context available: {', '.join(ctx_sources)}")

        # ── Build data summary (always needed for cache hash) ────────────
        _insight_lines = [f"Bank: {inst_name}, {inst_city} {inst_state}",
                          f"Total assets: {fmt_dep(inst_assets)}",
                          f"Established: {inst_est}",
                          f"Holding company: {inst_hc}" if inst_hc else ""]

        if not sod.empty:
            yr_dep = sod.groupby("YEAR")["DEPDOM"].first().sort_index()
            _insight_lines.append("Annual deposits ($K): " +
                                  ", ".join(f"{int(y)}: {int(v):,}" for y, v in yr_dep.items()))

        if not financials.empty:
            _insight_lines.append("\nRecent quarterly financials:")
            recent = financials.sort_values("date").tail(8)
            for _, r in recent.iterrows():
                parts = [f"Q{int(r['quarter'])} {int(r['year'])}"]
                for col, lbl in [("ASSET","Assets($K)"), ("DEP","Deposits($K)"),
                                 ("LNLSNET","Loans($K)"), ("NETINC","NetInc($K)"),
                                 ("ROA","ROA"), ("ROE","ROE"), ("NIMY","NIM"),
                                 ("EEFFR","Eff"), ("NTLNLSR","NPL"),
                                 ("NCLNLSR","NCO"), ("RBC1AAJ","T1Cap"),
                                 ("NUMEMP","Employees")]:
                    if col in r and pd.notna(r[col]):
                        if col in ["ASSET","DEP","LNLSNET","NETINC"]:
                            parts.append(f"{lbl}={int(r[col]):,}")
                        elif col == "NUMEMP":
                            parts.append(f"{lbl}={int(r[col])}")
                        else:
                            parts.append(f"{lbl}={r[col]:.2f}%")
                _insight_lines.append("  " + " | ".join(parts))

        if share is not None:
            _insight_lines.append(f"\nCurrent market share (all operating counties): {share:.2f}%")

        if not peers.empty:
            _insight_lines.append(f"\nPeer group: {len(peers)} banks, "
                                  f"scope: {peers['Peer Scope'].iloc[0] if 'Peer Scope' in peers.columns else 'N/A'}")
            for col, lbl in [("ROA","ROA"), ("ROE","ROE"), ("NIMY","NIM"), ("EEFFR","Efficiency")]:
                pm = peer_median(peers, col)
                if pm is not None:
                    _insight_lines.append(f"  Peer median {lbl}: {pm:.2f}%")

        if launch_year:
            _insight_lines.append(f"\nBrand launch year: {launch_year}")

        if not history.empty:
            _insight_lines.append("\nKey corporate events (FDIC history):")
            important_codes = ["1", "300", "310", "311", "312", "313",
                               "430", "470", "520", "530",
                               "711", "712", "713", "721", "722",
                               "810", "811", "820"]
            key_events = history[history["CHANGECODE"].astype(str).isin(important_codes)].copy()
            key_events = key_events.sort_values("EFFDATE", ascending=True)
            for _, ev in key_events.iterrows():
                date = str(ev.get("EFFDATE", ""))[:10]
                desc = ev.get("CHANGECODE_DESC", "")
                loc  = ev.get("OFF_NAME", "")
                city = ev.get("OFF_PCITY", "")
                loc_ok  = loc and pd.notna(loc) and str(loc).strip()
                city_ok = city and pd.notna(city) and str(city).strip()
                if loc_ok and city_ok:
                    loc_str = f" — {loc}, {city}"
                elif loc_ok:
                    loc_str = f" — {loc}"
                else:
                    loc_str = ""
                _insight_lines.append(f"  {date}: {desc}{loc_str}")

        _data_summary = "\n".join(_insight_lines)

        # Hash the inputs so we know when to invalidate
        _hash_input = _data_summary + _client_ctx + _industry_ctx
        _current_hash = hashlib.sha256(_hash_input.encode()).hexdigest()[:16]

        # ── Check cache ──────────────────────────────────────────────────
        _cached = fdic.get_cached_insights(cert)
        _cache_hit = (_cached is not None and _cached["input_hash"] == _current_hash)
        _do_generate = False

        if _cache_hit:
            _gen_dt = pd.Timestamp(_cached["generated_at"])
            _age_days = (pd.Timestamp.now() - _gen_dt).days
            st.caption(f"📋 Cached summary from {_gen_dt.strftime('%b %d, %Y')} "
                       f"({_age_days} day{'s' if _age_days != 1 else ''} ago) · "
                       f"Data unchanged since last generation")
            st.markdown(_cached["summary"])
            if st.button("↻ Regenerate",
                         help="Force a new AI summary even though the data hasn't changed"):
                _do_generate = True
                _cache_hit = False
        elif _cached is not None and _cached["input_hash"] != _current_hash:
            # Data has changed since last generation
            st.caption("⚠️ FDIC data or context has been updated since the last summary was generated.")
            col_gen, col_old = st.columns(2)
            with col_gen:
                _do_generate = st.button("Generate Updated Insights", type="primary")
            with col_old:
                _show_old = st.button("View Previous Summary")
            if _show_old:
                _gen_dt = pd.Timestamp(_cached["generated_at"])
                st.caption(f"📋 Previous summary from {_gen_dt.strftime('%b %d, %Y')} "
                           f"(data has changed since)")
                st.markdown(_cached["summary"])
                _do_generate = False
        else:
            _do_generate = st.button("Generate Insights", type="primary")

        if _do_generate:
            system_parts = [
                "You are a senior bank analyst at FMS, a financial marketing agency "
                "that works exclusively with community banks. You use FDIC data to "
                "evaluate client performance and brief the marketing strategy team.",
            ]
            if _industry_ctx:
                system_parts.append(
                    "\n\n## INDUSTRY CONTEXT\n"
                    "Use the following community banking industry data to put the "
                    "client's performance in context. Compare their metrics to industry "
                    "aggregates and note where they outperform or underperform the sector.\n\n"
                    + _industry_ctx
                )
            if _client_ctx:
                system_parts.append(
                    "\n\n## CLIENT CONTEXT (from Brand Discovery Report)\n"
                    "Use the following pre-summarized brand discovery research to enrich "
                    "your analysis. This includes the bank's growth strategy, market dynamics, "
                    "competitive positioning, acquisition history, and brand perception data "
                    "gathered through executive interviews, employee surveys, and customer "
                    "focus groups. Reference this context when explaining strategic decisions, "
                    "growth patterns, or competitive dynamics.\n\n"
                    + _client_ctx
                )

            prompt = f"""Here is the FDIC data summary for one of our clients:

{_data_summary}

Write a concise analyst memo (5–7 paragraphs) that:
1. Opens with a one-sentence characterisation of the bank's overall trajectory
2. Puts their performance in context — how do they compare to the community banking industry and their peer group? Are they outperforming or underperforming?
3. Explains any major inflection points visible in the data. Use the corporate events history to explain acquisitions, mergers, or branch activity that drove sudden changes. Do NOT present known events as mysteries.
4. Highlights the 2–3 most meaningful positive trends
5. Flags the 1–2 most important concerns or warning signs
6. If a brand launch date is present, comment on whether performance improved, held steady, or declined after the rebrand — but note that correlation is not causation
7. Closes with what this data suggests for the bank's near-term strategic focus from a marketing perspective

Write in plain English — no bullet points. Avoid restating every number; synthesise
what the data is actually telling us. The audience is a marketing strategist, not a regulator.
When referencing industry benchmarks, cite the specific year and metric (e.g. "the community bank median ROA was 0.95% in 2024")."""

            with st.spinner("Generating insights…"):
                client_ai = anthropic.Anthropic(api_key=api_key)
                response  = client_ai.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    system="\n".join(system_parts),
                    messages=[{"role": "user", "content": prompt}],
                )
            _summary_text = response.content[0].text
            fdic.save_insights(cert, _summary_text, _current_hash)
            st.markdown(_summary_text)
            st.caption(f"✅ Summary cached — will load instantly next time until data changes.")
