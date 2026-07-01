import streamlit as st
import pandas as pd
import requests
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="ShadowSense", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; font-family: 'MS Sans Serif', 'Arial', sans-serif; }
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
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG ---
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"

# Sidebar control — created once, OUTSIDE the fragment below. This is fine;
# the earlier bug was writing to the sidebar from *inside* a fragment.
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


# Everything auto-refreshing lives in ONE fragment, and nothing inside it
# writes to the sidebar — that keeps this safe from the sidebar/fragment
# restriction entirely, no workarounds needed.
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

    latest = df.iloc[-1]
    current_label = str(latest.get("label", "none")).lower()
    label_map = {"none": "No Shadow", "object": "Object", "weather": "Weather", "dust": "Dust / Haze"}
    display_label = label_map.get(current_label, "Unknown")

    st.markdown(f"""
        <div class="retro-card">
            <div style="font-size:24px; font-weight:bold; color:#000;">☀️ ShadowSense Diagnostic Utility</div>
            <div style="font-size:12px; color:#666;">Site A — Sepang Solar Farm, Selangor | [LIVE STATUS: RUNNING]</div>
        </div>
        """, unsafe_allow_html=True)

    # --- SNAPSHOT: native st.metric, no custom HTML needed ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Shadow Class", display_label)
    c2.metric("Temperature", f"{float(latest.get('temp', 0)):.1f}°C")
    c3.metric("R/B Ratio", f"{float(latest.get('rb', 0)):.2f}")
    c4.metric("Humidity", f"{float(latest.get('hum', 0)):.0f}%")
    c5.metric("Flatness", f"{float(latest.get('flat', 0)):.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown('<div class="retro-header">CLASSIFIER CONFIDENCE</div>', unsafe_allow_html=True)
        dom_pct = int(latest.get("dom_pct", 0))
        conf = pd.DataFrame(
            {"Confidence %": [dom_pct if current_label == k else 0
                              for k in ["none", "object", "weather", "dust"]]},
            index=["No Shadow", "Object", "Weather", "Dust / Haze"],
        )
        st.bar_chart(conf, horizontal=True)

    with right_col:
        st.markdown('<div class="retro-header">RECENT TEMPERATURE (°C)</div>', unsafe_allow_html=True)
        trend = df.tail(15).copy()
        if "timestamp" in trend.columns:
            trend["timestamp"] = trend["timestamp"].astype(str).str.slice(0, 19)
            trend = trend.set_index("timestamp")
        trend["temp"] = pd.to_numeric(trend.get("temp", 0), errors="coerce")
        st.line_chart(trend["temp"])

    st.markdown('<div class="retro-header">HISTORY (LAST 10 ENTRIES)</div>', unsafe_allow_html=True)
    show_cols = [c for c in ["timestamp", "label", "temp", "hum", "rb", "flat"] if c in df.columns]
    st.dataframe(df.tail(10).sort_index(ascending=False)[show_cols], use_container_width=True)

    st.caption(f"Last sync: {time.strftime('%H:%M:%S')}")


render_dashboard()

# --- FOOTER ---
st.markdown("""
    <div style="margin-top:25px; font-size:10px; color:#999; border-top:1px solid #ddd; padding-top:10px;">
        SYSTEM_ID: SHADOWSENSE_V1_STABLE | TELEMETRY_SOURCE: GOOGLE_APPS_SCRIPT_PROXY | RENDERING: STREAMLIT_CLOUD_NATIVE
    </div>
    """, unsafe_allow_html=True)
