import streamlit as st
import pandas as pd
import requests
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="ShadowSense", layout="wide")

st.markdown("""
    <style>
    /* Global Styles */
    .stApp { background-color: #fafafa; font-family: 'Segoe UI', 'Arial', sans-serif; color: #222222; }

    /* 90s Beveled Box Style */
    .retro-card {
        background-color: #f1f1f1;
        border: 2px solid;
        border-color: #ffffff #7b7b7b #7b7b7b #ffffff;
        padding: 18px;
        margin-bottom: 20px;
        border-radius: 2px;
    }

    .retro-header {
        background: linear-gradient(90deg, #ffccd5, #cceeff);
        padding: 6px 12px;
        border: 2px inset #fff;
        font-weight: bold;
        color: #222222;
        margin-bottom: 12px;
        font-size: 14px;
        letter-spacing: 0.5px;
    }

    /* Target native Streamlit metrics for cleaner look */
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #111111 !important; }
    [data-testid="stMetricLabel"] { font-size: 12px !important; color: #555555 !important; font-weight: 600 !important; }
    [data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 10px 15px;
        border: 2px inset #ffffff;
        border-radius: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG ---
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"
NUMERIC_COLS = ["temp", "hum", "rb", "flat"]

st.sidebar.header("🕹️ Comms Settings")
refresh_rate = st.sidebar.slider("Auto-refresh rate (seconds)", 5, 60, 10)


@st.cache_data(ttl=refresh_rate, show_spinner=False)
def fetch_sensor_data(url: str) -> pd.DataFrame:
    """Pull rows from the Google Sheet (via Apps Script JSON endpoint)."""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception as e:
        return pd.DataFrame({"__error__": [str(e)]})
    return pd.DataFrame()


def with_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the timestamp column into real datetimes, dropping unparsable rows."""
    out = df.copy()
    out["dt"] = pd.to_datetime(out.get("timestamp"), errors="coerce")
    return out.dropna(subset=["dt"])


def render_snapshot_and_charts(day_df: pd.DataFrame, header_note: str):
    """Renders the metric row + confidence/temperature charts + history table
    for whatever slice of data is passed in (a single day, in this app)."""
    latest = day_df.iloc[-1]
    current_label = str(latest.get("label", "none")).lower()
    label_map = {"none": "No Shadow", "object": "Object", "weather": "Weather", "dust": "Dust / Haze"}
    display_label = label_map.get(current_label, "Unknown")

    st.caption(header_note)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Shadow Class", display_label)
    c2.metric("Temperature", f"{float(latest.get('temp', 0)):.1f}°C")
    c3.metric("R/B Ratio", f"{float(latest.get('rb', 0)):.2f}")
    c4.metric("Humidity", f"{float(latest.get('hum', 0)):.0f}%")
    c5.metric("Flatness", f"{float(latest.get('flat', 0)):.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown('<div class="retro-header">CLASSIFIER CONFIDENCE (LATEST READING)</div>', unsafe_allow_html=True)
        dom_pct = int(latest.get("dom_pct", 0))
        conf = pd.DataFrame(
            {"Confidence %": [dom_pct if current_label == k else 0
                              for k in ["none", "object", "weather", "dust"]]},
            index=["No Shadow", "Object", "Weather", "Dust / Haze"],
        )
        st.bar_chart(conf, horizontal=True, color="#ffccd5", height=230)

    with right_col:
        st.markdown('<div class="retro-header">TEMPERATURE OVER SELECTED DAY (°C)</div>', unsafe_allow_html=True)
        trend = day_df.copy()
        trend["time"] = trend["dt"].dt.strftime("%H:%M:%S")
        trend = trend.set_index("time")
        trend["temp"] = pd.to_numeric(trend.get("temp", 0), errors="coerce")
        st.line_chart(trend["temp"], color="#bae1ff", height=230)

    st.markdown('<div class="retro-header">ENTRIES FOR SELECTED DAY</div>', unsafe_allow_html=True)
    show_cols = [c for c in ["timestamp", "label", "temp", "hum", "rb", "flat"] if c in day_df.columns]
    st.dataframe(
        day_df.sort_values("dt", ascending=False)[show_cols],
        use_container_width=True,
        hide_index=True,
    )


def render_period_average(df: pd.DataFrame, days: int, group_freq: str, group_label: str):
    """Shared renderer for the Weekly / Monthly average tabs."""
    cutoff = df["dt"].max() - pd.Timedelta(days=days)
    period_df = df[df["dt"] >= cutoff].copy()

    if period_df.empty:
        st.info(f"Not enough data yet to compute a {group_label.lower()} average.")
        return

    st.caption(
        f"Averaging {len(period_df)} readings from "
        f"{period_df['dt'].min().strftime('%Y-%m-%d')} to {period_df['dt'].max().strftime('%Y-%m-%d')}"
    )

    for col in NUMERIC_COLS:
        period_df[col] = pd.to_numeric(period_df.get(col), errors="coerce")

    averages = period_df[NUMERIC_COLS].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Temperature", f"{averages.get('temp', 0):.1f}°C")
    c2.metric("Avg Humidity", f"{averages.get('hum', 0):.0f}%")
    c3.metric("Avg R/B Ratio", f"{averages.get('rb', 0):.2f}")
    c4.metric("Avg Flatness", f"{averages.get('flat', 0):.2f}")

    st.markdown(f'<div class="retro-header">{group_label.upper()} BREAKDOWN — AVG TEMPERATURE (°C)</div>', unsafe_allow_html=True)
    breakdown = (
        period_df.set_index("dt")[NUMERIC_COLS]
        .resample(group_freq)
        .mean()
    )
    breakdown.index = breakdown.index.strftime("%Y-%m-%d")
    st.bar_chart(breakdown["temp"], color="#ffccd5", height=230)

    if "label" in period_df.columns:
        st.markdown('<div class="retro-header">SHADOW CLASS DISTRIBUTION</div>', unsafe_allow_html=True)
        counts = period_df["label"].astype(str).str.lower().value_counts()
        label_map = {"none": "No Shadow", "object": "Object", "weather": "Weather", "dust": "Dust / Haze"}
        counts.index = [label_map.get(i, i) for i in counts.index]
        st.bar_chart(counts, color="#cceeff", height=200)


@st.fragment(run_every=refresh_rate)
def render_dashboard():
    df = fetch_sensor_data(API_URL)

    if "__error__" in df.columns:
        st.markdown(f"""
            <div class="retro-card" style="border-color: #ffffff #ef4444 #ef4444 #ffffff;">
                <div style="color:#b91c1c; font-weight:bold;">⚠️ TELEMETRY CONNECTION ERROR</div>
                <div style="font-size:12px; color:#666; margin-top:5px;">{df['__error__'].iloc[0]}</div>
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"Last attempted sync: {time.strftime('%H:%M:%S')}")
        return

    if df.empty:
        st.markdown("""
            <div class="retro-card" style="border-color: #ffffff #ef4444 #ef4444 #ffffff;">
                <div style="color:#b91c1c; font-weight:bold;">⚠️ NO DATA YET</div>
                <div style="font-size:12px; color:#666; margin-top:5px;">Waiting for the first row to land in the sheet...</div>
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"Last checked: {time.strftime('%H:%M:%S')}")
        return

    df = with_datetime(df)
    if df.empty:
        st.warning("Rows are arriving, but none have a parsable 'timestamp' value — date filtering and averages need that column.")
        return

    st.markdown("""
        <div class="retro-card">
            <div style="font-size:24px; font-weight:bold; color:#111111; letter-spacing:-0.5px;">☀️ ShadowSense Diagnostic Utility</div>
            <div style="font-size:12px; color:#555555; margin-top:4px;">Site A — Sepang Solar Farm, Selangor | [LIVE STATUS: RUNNING]</div>
        </div>
        """, unsafe_allow_html=True)

    tab_daily, tab_weekly, tab_monthly = st.tabs(["📅 Daily", "📊 Weekly Average", "🗓️ Monthly Average"])

    with tab_daily:
        available_dates = sorted(df["dt"].dt.date.unique())
        selected_date = st.date_input(
            "Select date",
            value=available_dates[-1],
            min_value=available_dates[0],
            max_value=available_dates[-1],
        )
        day_df = df[df["dt"].dt.date == selected_date]

        if day_df.empty:
            st.info("No readings recorded for that date.")
        else:
            render_snapshot_and_charts(day_df, header_note=f"Showing {len(day_df)} reading(s) for {selected_date}")

    with tab_weekly:
        render_period_average(df, days=7, group_freq="D", group_label="Daily")

    with tab_monthly:
        render_period_average(df, days=30, group_freq="W", group_label="Weekly")

    st.caption(f"Last sync: {time.strftime('%H:%M:%S')}")


render_dashboard()

# --- FOOTER ---
st.markdown("""
    <div style="margin-top:35px; font-size:10px; color:#888888; border-top:1px solid #ddd; padding-top:10px; letter-spacing:0.3px;">
        SYSTEM_ID: SHADOWSENSE_V1_STABLE | TELEMETRY_SOURCE: GOOGLE_APPS_SCRIPT_PROXY | RENDERING: STREAMLIT_CLOUD_NATIVE
    </div>
    """, unsafe_allow_html=True)
