import streamlit as st
import pandas as pd
import requests
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="ShadowSense", layout="wide")

# --- THEME-AWARE STYLING -----------------------------------------------
# Base surfaces (background/card/text) come from Streamlit's own CSS
# variables, which already track whichever theme the user has selected
# (light / dark / system) — that's why .stApp no longer hardcodes a
# background or text color like the previous version did.
#
# The pastel accent colors are custom, so Streamlit doesn't expose those.
# They get a light-mode default plus a dark-mode override driven by
# prefers-color-scheme, which matches the OS setting. If someone manually
# flips only the in-app Streamlit theme (leaving the OS on the opposite
# mode), the accents may not perfectly match — a known trade-off of using
# custom colors alongside Streamlit's theme system.
st.markdown("""
    <style>
    :root {
        --accent-yellow: #fffacd;
        --accent-pink:   #ffe4e6;
        --accent-green:  #dcfce7;
        --accent-blue:   #dbeafe;
        --accent-lime:   #f0fdf4;
        --accent-orange: #fff7ed;
        --warn-color: #b45309;
        --good-color: #166534;
        --info-color: #1e40af;
        --track-bg: #e0e0e0;
        --hairline: #dddddd;
        --border-hi: rgba(255,255,255,0.7);
        --border-lo: rgba(0,0,0,0.35);
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --accent-yellow: #4a4020;
            --accent-pink:   #4a2530;
            --accent-green:  #1f3a28;
            --accent-blue:   #1e2f4a;
            --accent-lime:   #223322;
            --accent-orange: #3a2c1f;
            --warn-color: #fbbf24;
            --good-color: #4ade80;
            --info-color: #93c5fd;
            --track-bg: #333333;
            --hairline: #444444;
            --border-hi: rgba(255,255,255,0.18);
            --border-lo: rgba(0,0,0,0.6);
        }
    }

    .stApp { font-family: 'Segoe UI', 'Arial', sans-serif; }

    .retro-card {
        background-color: var(--secondary-background-color, #f1f1f1);
        border: 2px solid;
        border-color: var(--border-hi) var(--border-lo) var(--border-lo) var(--border-hi);
        padding: 18px;
        margin-bottom: 20px;
        border-radius: 2px;
        color: var(--text-color);
    }

    .retro-header {
        background: linear-gradient(90deg, var(--accent-pink), var(--accent-blue));
        padding: 6px 12px;
        border: 2px inset var(--border-hi);
        font-weight: bold;
        color: var(--text-color);
        margin-bottom: 12px;
        font-size: 14px;
        letter-spacing: 0.5px;
    }

    .metric-box {
        border: 2px solid;
        border-color: var(--border-lo) var(--border-hi) var(--border-hi) var(--border-lo);
        padding: 10px 12px;
        text-align: center;
        border-radius: 2px;
        height: 100%;
    }
    .met-lbl { font-size: 11px; color: var(--text-color); opacity: 0.7; margin-bottom: 4px; }
    .met-val { font-size: 20px; font-weight: bold; color: var(--text-color); line-height: 1.15; }
    .met-sub { font-size: 10px; margin-top: 4px; opacity: 0.85; }

    .badge {
        display: inline-block;
        font-size: 12px;
        padding: 2px 10px;
        border: 1px solid;
        font-weight: bold;
        border-radius: 2px;
    }

    .note {
        font-size: 11px;
        opacity: 0.75;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        padding: 6px 10px;
        border: 1px solid var(--hairline);
        border-radius: 2px;
        color: var(--text-color);
    }

    .warn { color: var(--warn-color); }
    .good { color: var(--good-color); }
    .info-txt { color: var(--info-color); }

    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 5px; font-size: 13px; border-bottom: 1px solid var(--hairline); color: var(--text-color); }

    .bar-container { width: 100%; background-color: var(--track-bg); border: 1px solid var(--border-lo); height: 16px; }
    .bar-fill { height: 100%; }

    /* Native Streamlit metric widget — nudge sizing only, let it inherit theme colors */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color, #f8f9fa);
        padding: 10px 15px;
        border: 2px inset var(--border-hi);
        border-radius: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG ---
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"
NUMERIC_COLS = ["temp", "hum", "rb", "flat"]
LABEL_MAP = {"none": "No Shadow", "object": "Object", "weather": "Weather", "dust": "Dust / Haze"}

# Thresholds used only for the little "warn / good" sub-labels on metric
# cards — tune freely, they don't affect the underlying data.
TEMP_WARN_C = 35.0
FLATNESS_LOW = 0.30

# Spectral / irradiance columns your sheet doesn't populate yet. If you add
# these to the sheet later, the corresponding panels below will pick them
# up automatically — no code changes needed.
SPECTRAL_COLS = ["ch415", "ch445", "ch480", "ch515", "ch555", "ch630", "ch680", "nir"]
IRRADIANCE_COL = "irradiance"
CLEAR_SKY_COL = "clear_sky"

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


def metric_card(col, label, value, accent, sub=None, sub_class=""):
    """Custom pastel metric card (theme-aware), mirroring the draft's snapshot boxes."""
    sub_html = f'<div class="met-sub {sub_class}">{sub}</div>' if sub else ""
    col.markdown(f"""
        <div class="metric-box" style="background-color: var(--accent-{accent});">
            <div class="met-lbl">{label}</div>
            <div class="met-val">{value}</div>
            {sub_html}
        </div>
        """, unsafe_allow_html=True)


def render_snapshot(latest: pd.Series):
    """Snapshot grid — metrics per your friend's list, plus Humidity as a bonus."""
    current_label = str(latest.get("label", "none")).lower()
    display_label = LABEL_MAP.get(current_label, "Unknown")
    dom_pct = int(latest.get("dom_pct", 0)) if pd.notna(latest.get("dom_pct", None)) else None

    temp = latest.get("temp")
    temp = float(temp) if pd.notna(temp) else None
    rb = latest.get("rb")
    rb = float(rb) if pd.notna(rb) else None
    flat = latest.get("flat")
    flat = float(flat) if pd.notna(flat) else None
    hum = latest.get("hum")
    hum = float(hum) if pd.notna(hum) else None
    clear_sky = latest.get(CLEAR_SKY_COL)
    clear_sky = float(clear_sky) if pd.notna(clear_sky) else None

    st.markdown('<p style="font-weight:bold; font-size:14px; margin-bottom:8px;">📊 CURRENT SNAPSHOT</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    metric_card(
        c1, "Shadow Class",
        f'<span class="badge" style="background-color:var(--accent-yellow); border-color:var(--warn-color); color:var(--warn-color);">{display_label}</span>',
        "yellow",
        sub=f"Conf. {dom_pct}%" if dom_pct is not None else "Conf. N/A",
        sub_class="warn" if dom_pct else "",
    )
    metric_card(
        c2, "Temperature",
        f"{temp:.1f}°C" if temp is not None else "N/A",
        "pink",
        sub=("Above 35°C" if temp is not None and temp > TEMP_WARN_C else "Normal range") if temp is not None else None,
        sub_class="warn" if (temp is not None and temp > TEMP_WARN_C) else "good",
    )
    metric_card(
        c3, "R/B Ratio",
        f"{rb:.2f}" if rb is not None else "N/A",
        "green",
    )
    metric_card(
        c4, "Clear Sky",
        f"{clear_sky:.0f}%" if clear_sky is not None else "N/A",
        "blue",
        sub="of daylight hrs" if clear_sky is not None else "sensor not connected yet",
    )
    metric_card(
        c5, "Spectral Flatness",
        f"{flat:.2f}" if flat is not None else "N/A",
        "lime",
        sub=("Low — uneven" if flat is not None and flat < FLATNESS_LOW else "Even") if flat is not None else None,
        sub_class="warn" if (flat is not None and flat < FLATNESS_LOW) else "good",
    )
    metric_card(
        c6, "Humidity",
        f"{hum:.0f}%" if hum is not None else "N/A",
        "orange",
        sub="extra — from sensor",
    )


def render_classifier_confidence(latest: pd.Series):
    st.markdown('<div class="retro-header">CLASSIFIER CONFIDENCE (LATEST READING)</div>', unsafe_allow_html=True)
    current_label = str(latest.get("label", "none")).lower()
    dom_pct = int(latest.get("dom_pct", 0)) if pd.notna(latest.get("dom_pct", None)) else 0

    colors = {"none": "var(--accent-green)", "object": "var(--accent-pink)",
              "weather": "var(--accent-blue)", "dust": "var(--accent-yellow)"}
    table_html = "<table>"
    for key, name in LABEL_MAP.items():
        val = dom_pct if current_label == key else 0
        table_html += f"""
            <tr>
                <td width="30%">{name}</td>
                <td width="60%">
                    <div class="bar-container"><div class="bar-fill" style="width:{val}%; background-color:{colors[key]};"></div></div>
                </td>
                <td width="10%">{val}%</td>
            </tr>
        """
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)


def render_spectral_channels(latest: pd.Series):
    """From the draft's 'Spectral Channels (AS7341)' panel. Falls back to an
    honest placeholder if the sheet doesn't have raw channel columns yet."""
    st.markdown('<div class="retro-header">SPECTRAL CHANNELS (AS7341)</div>', unsafe_allow_html=True)
    present = [c for c in SPECTRAL_COLS if c in latest.index and pd.notna(latest.get(c))]

    if not present:
        st.markdown("""
            <div class="note">ℹ️ Raw spectral channel data not available yet — add AS7341 channel columns (e.g. ch415, ch445, ... nir) to the sheet to enable this panel.</div>
            """, unsafe_allow_html=True)
        rb = latest.get("rb")
        if pd.notna(rb):
            st.caption(f"Only the aggregate R/B ratio is available right now: **{float(rb):.2f}**")
        return

    channel_colors = {
        "ch415": "#7c3aed", "ch445": "#4f7dde", "ch480": "#2d8fe0", "ch515": "#22b87a",
        "ch555": "#85c020", "ch630": "#e05030", "ch680": "#c02020", "nir": "#888888",
    }
    max_val = max(float(latest[c]) for c in present) or 1
    spec_html = "<table>"
    for c in present:
        val = float(latest[c])
        pct = min(100, (val / max_val) * 100)
        spec_html += f"""
            <tr>
                <td width="20%">{c}</td>
                <td><div class="bar-container"><div class="bar-fill" style="width:{pct:.0f}%; background-color:{channel_colors.get(c, '#888')};"></div></div></td>
                <td width="15%">{val:.0f}</td>
            </tr>
        """
    spec_html += "</table>"
    st.markdown(spec_html, unsafe_allow_html=True)


def render_irradiance_trend(day_df: pd.DataFrame):
    """From the draft's 'Irradiance Loss Trend (Hourly)' panel. Falls back to
    an honest placeholder if there's no irradiance column in the sheet."""
    st.markdown('<div class="retro-header">IRRADIANCE LOSS TREND (HOURLY)</div>', unsafe_allow_html=True)

    if IRRADIANCE_COL not in day_df.columns or day_df[IRRADIANCE_COL].isna().all():
        st.markdown("""
            <div class="note">ℹ️ Irradiance data not shown — requires an irradiance/pyranometer sensor column in the sheet (future upgrade).</div>
            """, unsafe_allow_html=True)
        return

    hourly = day_df.set_index("dt")[IRRADIANCE_COL].apply(pd.to_numeric, errors="coerce").resample("h").mean().dropna()
    if hourly.empty:
        st.caption("No irradiance readings for this day yet.")
        return

    loss_html = "<table><tr>"
    for ts, val in hourly.items():
        color = "#baffc9" if val >= 80 else ("#fffacd" if val >= 50 else "#ffb3ba")
        loss_html += f"""
            <td style="text-align:center; border-bottom:none;">
                <div style="height:100px; display:flex; align-items:flex-end; justify-content:center; background:var(--track-bg); border:1px inset var(--border-hi); padding:2px;">
                    <div style="width:30px; height:{min(100, max(4, val)):.0f}%; background-color:{color}; border:1px solid var(--border-lo);"></div>
                </div>
                <div style="font-size:10px; margin-top:5px; color:var(--text-color);">{ts.strftime('%H:%M')}<br><b>{val:.0f}%</b></div>
            </td>
        """
    loss_html += "</tr></table>"
    st.markdown(loss_html, unsafe_allow_html=True)


def render_snapshot_and_charts(day_df: pd.DataFrame, header_note: str):
    """Full daily view: snapshot + all draft panels, scoped to one day's data."""
    latest = day_df.iloc[-1]
    st.caption(header_note)

    render_snapshot(latest)
    st.markdown("<br>", unsafe_allow_html=True)

    left_col, right_col = st.columns(2)
    with left_col:
        render_classifier_confidence(latest)
    with right_col:
        render_spectral_channels(latest)

    st.markdown("<br>", unsafe_allow_html=True)

    left_col2, right_col2 = st.columns(2)
    with left_col2:
        st.markdown('<div class="retro-header">TEMPERATURE OVER SELECTED DAY (°C)</div>', unsafe_allow_html=True)
        trend = day_df.copy()
        trend["time"] = trend["dt"].dt.strftime("%H:%M:%S")
        trend = trend.set_index("time")
        trend["temp"] = pd.to_numeric(trend.get("temp", 0), errors="coerce")
        st.line_chart(trend["temp"], color="#bae1ff", height=230)
    with right_col2:
        render_irradiance_trend(day_df)

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
        counts.index = [LABEL_MAP.get(i, i) for i in counts.index]
        st.bar_chart(counts, color="#cceeff", height=200)


@st.fragment(run_every=refresh_rate)
def render_dashboard():
    df = fetch_sensor_data(API_URL)

    if "__error__" in df.columns:
        st.markdown(f"""
            <div class="retro-card" style="border-color: #ffffff #ef4444 #ef4444 #ffffff;">
                <div class="warn" style="font-weight:bold;">⚠️ TELEMETRY CONNECTION ERROR</div>
                <div style="font-size:12px; margin-top:5px;">{df['__error__'].iloc[0]}</div>
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"Last attempted sync: {time.strftime('%H:%M:%S')}")
        return

    if df.empty:
        st.markdown("""
            <div class="retro-card" style="border-color: #ffffff #ef4444 #ef4444 #ffffff;">
                <div class="warn" style="font-weight:bold;">⚠️ NO DATA YET</div>
                <div style="font-size:12px; margin-top:5px;">Waiting for the first row to land in the sheet...</div>
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
            <div style="font-size:24px; font-weight:bold; letter-spacing:-0.5px;">☀️ ShadowSense Diagnostic Utility</div>
            <div style="font-size:12px; opacity:0.7; margin-top:4px;">Site A — Sepang Solar Farm, Selangor | [LIVE STATUS: RUNNING]</div>
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
    <div style="margin-top:35px; font-size:10px; opacity:0.6; border-top:1px solid var(--hairline); padding-top:10px; letter-spacing:0.3px;">
        SYSTEM_ID: SHADOWSENSE_V1_STABLE | TELEMETRY_SOURCE: GOOGLE_APPS_SCRIPT_PROXY | RENDERING: STREAMLIT_CLOUD_NATIVE
    </div>
    """, unsafe_allow_html=True)
