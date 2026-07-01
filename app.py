import streamlit as st
import pandas as pd
import requests
import time

# --- 90s RETRO PASTEL STYLING ---
st.set_page_config(page_title="ShadowSense v1.0", layout="wide")

st.markdown("""
    <style>
    /* Global Styles Override */
    .stApp { background-color: #ffffff; font-family: 'MS Sans Serif', 'Arial', sans-serif; }

    /* 90s Beveled Box Style */
    .retro-card {
        background-color: #f3f3f3;
        border: 2px solid;
        border-color: #ffffff #808080 #808080 #ffffff;
        padding: 15px;
        margin-bottom: 15px;
    }

    .retro-header {
        background: linear-gradient(90deg, #ffb3ba, #bae1ff);
        padding: 5px 10px;
        border: 2px inset #fff;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
    }

    /* Pastel Metrics */
    .metric-box {
        text-align: center;
        padding: 10px;
        border: 2px inset #fff;
        background-color: #fafafa;
        margin-bottom: 10px;
    }

    /* Bar Table Styling */
    .bar-container { width: 100%; background-color: #e0e0e0; border: 1px solid #808080; height: 18px; }
    .bar-fill { height: 100%; }

    table { width: 100%; border-collapse: collapse; }
    td { padding: 5px; font-size: 13px; border-bottom: 1px solid #ddd; color: #333333; }
    th { padding: 5px; font-size: 13px; border-bottom: 2px solid #808080; color: #000000; text-align: left;}
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURATION & INGESTION ---
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"

# Sidebar interval configurations
st.sidebar.header("🕹️ Comms Settings")
refresh_rate = st.sidebar.slider("Auto-refresh rate (seconds)", 5, 60, 10)


# Cache the raw fetch itself so a burst of reruns within the TTL window
# doesn't hammer the Apps Script endpoint. TTL tracks the chosen refresh rate.
@st.cache_data(ttl=refresh_rate, show_spinner=False)
def fetch_sensor_data(url: str) -> pd.DataFrame:
    try:
        response = requests.get(url, timeout=15)  # Apps Script can be slow, esp. cold starts
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception as e:
        return pd.DataFrame({"__error__": [str(e)]})
    return pd.DataFrame()


# A fragment can only write to the sidebar if it is invoked from inside a
# `with st.sidebar:` block (see call site near the bottom of the file).
# Keeping this fragment separate from the main dashboard fragment below lets
# each one write to its own area without tripping that restriction.
@st.fragment(run_every=refresh_rate)
def render_sidebar_status():
    df = fetch_sensor_data(API_URL)  # served from cache in the common case
    if "__error__" in df.columns:
        st.error(f"Link Fault: {df['__error__'].iloc[0]}")
    st.caption(f"Last sync: {time.strftime('%H:%M:%S')}")


# Everything that should auto-refresh lives inside this fragment.
# run_every triggers a lightweight rerun of *just this fragment* on a timer,
# instead of blocking the thread with time.sleep + a full st.rerun().
@st.fragment(run_every=refresh_rate)
def render_dashboard():
    df = fetch_sensor_data(API_URL)

    if "__error__" in df.columns:
        df = pd.DataFrame()

    if not df.empty:
        # Extract the absolute latest summary record
        latest = df.iloc[-1]

        # Map the incoming data safely
        current_label = str(latest.get('label', 'none')).lower()
        dom_pct = int(latest.get('dom_pct', 0))
        temp = float(latest.get('temp', 0.0))
        hum = float(latest.get('hum', 0.0))
        rb_ratio = float(latest.get('rb', 0.0))
        flatness = float(latest.get('flat', 0.0))

        # Map labels to human-readable format
        label_map = {"none": "No Shadow", "object": "Object", "weather": "Weather", "dust": "Dust / Haze"}
        display_label = label_map.get(current_label, "Unknown")

        # --- HEADER ---
        st.markdown(f"""
            <div class="retro-card">
                <div style="font-size: 24px; font-weight: bold; color: #000000;">☀️ ShadowSense Diagnostic Utility</div>
                <div style="font-size: 12px; color: #666;">Site A — Sepang Solar Farm, Selangor | [LIVE STATUS: RUNNING]</div>
            </div>
            """, unsafe_allow_html=True)

        # --- SNAPSHOT GRID ---
        st.markdown('<p style="font-weight:bold; font-size:14px; margin-bottom:5px; color:#000;">CURRENT SNAPSHOT</p>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        metrics = [
            ("Shadow Class", display_label, "#ffffba"),      # Pastel Yellow
            ("Temperature", f"{temp}°C", "#ffb3ba"),         # Pastel Red
            ("R/B Ratio", f"{rb_ratio:.2f}", "#baffc9"),      # Pastel Green
            ("Humidity", f"{hum}%", "#bae1ff"),              # Pastel Blue
            ("Flatness", f"{flatness:.2f}", "#e1f7d5"),       # Pale Green
            ("Dominance", f"{dom_pct}%", "#ffdfba")           # Pastel Orange
        ]

        for i, col in enumerate([c1, c2, c3, c4, c5, c6]):
            with col:
                st.markdown(f"""
                    <div class="metric-box" style="background-color: {metrics[i][2]};">
                        <div style="font-size:11px; color:#555;">{metrics[i][0]}</div>
                        <div style="font-size:18px; font-weight:bold; color:#000;">{metrics[i][1]}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- TWO COLUMN DATA SECTION ---
        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown('<div class="retro-header">CLASSIFIER WINNER CONFIDENCE (CURRENT SUMMARY)</div>', unsafe_allow_html=True)

            classes = [
                ("No Shadow", dom_pct if current_label == "none" else 0, "#baffc9"),
                ("Object", dom_pct if current_label == "object" else 0, "#ffb3ba"),
                ("Weather", dom_pct if current_label == "weather" else 0, "#bae1ff"),
                ("Dust / Haze", dom_pct if current_label == "dust" else 0, "#ffffba")
            ]

            table_html = "<table>"
            for name, val, color in classes:
                table_html += f"""
                    <tr>
                        <td width="30%">{name}</td>
                        <td width="60%">
                            <div class="bar-container"><div class="bar-fill" style="width:{val}%; background-color:{color};"></div></div>
                        </td>
                        <td width="10%">{val}%</td>
                    </tr>
                """
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="retro-header">HISTORIC OVERVIEW LOG (LAST 5 ENTRIES)</div>', unsafe_allow_html=True)

            history_df = df.tail(5).sort_index(ascending=False)
            hist_html = """
            <table>
                <tr>
                    <th><b>Timestamp</b></th>
                    <th><b>Label</b></th>
                    <th><b>R/B</b></th>
                    <th><b>Flat</b></th>
                    <th><b>Temp</b></th>
                </tr>
            """
            for _, row in history_df.iterrows():
                ts_trimmed = str(row.get('timestamp', ''))[:19].replace('T', ' ')
                lbl = str(row.get('label', '')).upper()
                hist_html += f"""
                    <tr>
                        <td>{ts_trimmed}</td>
                        <td style="color:#059669; font-weight:bold;">{lbl}</td>
                        <td>{float(row.get('rb', 0.0)):.2f}</td>
                        <td>{float(row.get('flat', 0.0)):.2f}</td>
                        <td>{float(row.get('temp', 0.0)):.1f}°C</td>
                    </tr>
                """
            hist_html += "</table>"
            st.markdown(hist_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- HISTORICAL TEMPERATURE PROFILE TREND ---
        st.markdown('<div class="retro-header">HISTORICAL TEMPERATURE TREND BAR DIAGRAM (LAST 6 SUMMARY INTERVALS)</div>', unsafe_allow_html=True)

        trend_slice = df.tail(6)

        loss_html = "<table><tr>"
        for idx, row in trend_slice.iterrows():
            t_val = float(row.get('temp', 0.0))
            pct_height = min(100, max(10, int((t_val / 50.0) * 100)))

            loss_html += f"""
                <td style="text-align:center; border-bottom:none;">
                    <div style="height:120px; display:flex; align-items:flex-end; justify-content:center; background:#eee; border:1px inset #fff; padding:4px;">
                        <div style="width:45px; height:{pct_height}%; background-color:#ffb3ba; border:1px solid #808080;"></div>
                    </div>
                    <div style="font-size:11px; margin-top:5px; color:#333;">Point {idx}<br><b>{t_val:.1f}°C</b></div>
                </td>
            """
        loss_html += "</tr></table>"
        st.markdown(loss_html, unsafe_allow_html=True)

    else:
        st.markdown("""
            <div class="retro-card" style="border-color: #ffffff #ef4444 #ef4444 #ffffff;">
                <div style="color: #b91c1c; font-weight: bold;">⚠️ TELEMETRY CONNECTION ERROR</div>
                <div style="font-size: 12px; color: #666; margin-top:5px;">Awaiting incoming streaming data arrays from remote micro-controller nodes...</div>
            </div>
            """, unsafe_allow_html=True)


with st.sidebar:
    render_sidebar_status()

render_dashboard()

# --- FOOTER ---
st.markdown("""
    <div style="margin-top:25px; font-size:10px; color:#999; border-top: 1px solid #ddd; padding-top:10px;">
        SYSTEM_ID: SHADOWSENSE_V1_STABLE | TELEMETRY_SOURCE: GOOGLE_APPS_SCRIPT_PROXY | RENDERING: STREAMLIT_CLOUD_NATIVE
    </div>
    """, unsafe_allow_html=True)
