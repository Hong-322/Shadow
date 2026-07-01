import streamlit as st
import pandas as pd
import requests
import time

# --- 90s RETRO PASTEL STYLING ---
st.set_page_config(page_title="ShadowSense v1.0", layout="wide")

st.markdown("""
    <style>
    /* Global Styles */
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
    }
    
    /* Bar Table Styling */
    .bar-container { width: 100%; background-color: #e0e0e0; border: 1px solid #808080; height: 18px; }
    .bar-fill { height: 100%; }
    
    table { width: 100%; border-collapse: collapse; }
    td { padding: 5px; font-size: 13px; border-bottom: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
    <div class="retro-card">
        <div style="font-size: 24px; font-weight: bold;">☀️ ShadowSense Diagnostic Utility</div>
        <div style="font-size: 12px; color: #666;">Site A — Sepang Solar Farm, Selangor | [LIVE STATUS: ACTIVE]</div>
    </div>
    """, unsafe_allow_html=True)

# 🔗 GOOGLE APPS SCRIPT WEB APP URL
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"

# Setup sidebar configuration
st.sidebar.header("Dashboard Controls")
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 10)

# Function to fetch data from your Google Script
def fetch_sensor_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception as e:
        st.sidebar.error(f"Sync Connection Failed: {e}")
    return pd.DataFrame()

# Fetch latest live data from Google Sheets
df = fetch_sensor_data(API_URL)

if not df.empty:
    # Safely convert timestamp string records to DateTime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Isolate the latest single sample record row
    latest = df.iloc[-1]
    
    # Process string transformations for labels
    current_label = str(latest['label']).lower()
    
    # --- SNAPSHOT GRID ---
    st.markdown('<p style="font-weight:bold; font-size:14px; margin-bottom:5px;">CURRENT SNAPSHOT</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    metrics = [
        ("Shadow Class", str(latest['label']).upper(), "#ffffba"),      # Pastel Yellow
        ("Temperature", f"{latest['temp']}°C", "#ffb3ba"),              # Pastel Red
        ("R/B Ratio", f"{latest['rb']:.3f}", "#baffc9"),                # Pastel Green
        ("Dominance", f"{latest['dom_pct']}%", "#bae1ff"),              # Pastel Blue
        ("Flatness", f"{latest['flat']:.3f}", "#e1f7d5"),               # Pale Green
        ("Humidity", f"{latest['hum']}%", "#ffdfba")                   # Pastel Orange
    ]

    for i, col in enumerate([c1, c2, c3, c4, c5, c6]):
        with col:
            st.markdown(f"""
                <div class="metric-box" style="background-color: {metrics[i][2]};">
                    <div style="font-size:11px; color:#555;">{metrics[i][0]}</div>
                    <div style="font-size:18px; font-weight:bold;">{metrics[i][1]}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TWO COLUMN DATA SECTION ---
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown('<div class="retro-header">CLASSIFIER CONFIDENCE (LIVE VOTE)</div>', unsafe_allow_html=True)
        
        # Determine confidence levels dynamically based on the current winning label
        pct = int(latest['dom_pct'])
        other_pct = (100 - pct) // 3 # Sub-allocate remaining weight to other slots for styling visual depth
        
        classes = [
            ("No Shadow", pct if current_label == "none" else other_pct, "#baffc9"),
            ("Object", pct if current_label == "object" else other_pct, "#ffb3ba"),
            ("Weather", pct if current_label == "weather" else other_pct, "#bae1ff"),
            ("Dust / Haze", pct if current_label == "dust" else other_pct, "#ffffba")
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
        st.markdown('<div class="retro-header">SPECTRAL METRICS ANALYSIS SUMMARY</div>', unsafe_allow_html=True)
        
        # Map structural ratio values to bar scaling (Clamped 0.0 - 2.0 to 0 - 100% frame fill bounds)
        rb_bar_val = min(100, int((float(latest['rb']) / 2.0) * 100))
        flat_bar_val = min(100, int(float(latest['flat']) * 100))
        
        spec_html = f"""
        <table>
            <tr>
                <td width="30%">Red/Blue Ratio</td>
                <td>
                    <div class="bar-container"><div class="bar-fill" style="width:{rb_bar_val}%; background-color:#e05030;"></div></div>
                </td>
                <td width="15%">{latest['rb']:.3f}</td>
            </tr>
            <tr>
                <td width="30%">Spectral Flatness</td>
                <td>
                    <div class="bar-container"><div class="bar-fill" style="width:{flat_bar_val}%; background-color:#4f7dde;"></div></div>
                </td>
                <td width="15%">{latest['flat']:.3f}</td>
            </tr>
        </table>
        """
        st.markdown(spec_html, unsafe_allow_html=True)

    # --- HISTORICAL TEMPERATURE PROFILE TREND ---
    st.markdown('<div class="retro-header">HISTORICAL TEMPERATURE TREND PROFILE (LAST 6 SUMMARIES)</div>', unsafe_allow_html=True)

    # Pull out up to the last 6 data entries dynamically
    history_df = df.tail(6)
    
    loss_html = "<table><tr>"
    for idx, row in history_df.iterrows():
        # Clean relative timestamp label output strings
        t_label = row['timestamp'].strftime('%H:%M:%S')
        val = float(row['temp'])
        
        # Determine bar fill coloring profile based on threshold values
        color = "#ffb3ba" if val > 35.0 else "#baffc9"
        
        # Scale dynamic graph pixel heights safely relative to normal outdoor operating scopes (e.g., max 50C)
        height_pct = min(100, int((val / 50.0) * 100))
        
        loss_html += f"""
            <td style="text-align:center; border-bottom:none;">
                <div style="height:100px; display:flex; align-items:flex-end; justify-content:center; background:#eee; border:1px inset #fff; padding:2px;">
                    <div style="width:45px; height:{height_pct}%; background-color:{color}; border:1px solid #808080;"></div>
                </div>
                <div style="font-size:10px; margin-top:5px;">{t_label}<br><b>{val:.1f}°C</b></div>
            </td>
        """
    loss_html += "</tr></table>"
    st.markdown(loss_html, unsafe_allow_html=True)

else:
    st.warning("⚠️ CRITICAL: Awaiting active telemetry packet stream data values from Google Sheets storage array...")

# --- FOOTER ---
st.markdown("""
    <div style="margin-top:20px; font-size:10px; color:#999; border-top: 1px solid #ddd; padding-top:10px;">
        SYSTEM_ID: SHADOWSENSE_V1_STABLE | TELEMETRY_LINK: GOOGLE_APPS_SCRIPT_WEB_APP | INA226_EMULATED
    </div>
    """, unsafe_allow_html=True)

# Auto-refresh loop engine injection 
time.sleep(refresh_rate)
st.rerun()
