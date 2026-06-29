import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time

# Configure page layout
st.set_page_config(page_title="ShadowSense Analytics", layout="wide")

# 🔗 PASTE YOUR GOOGLE APPS SCRIPT WEB APP URL HERE
API_URL = "https://script.google.com/macros/s/AKfycbywN4bkrHGWLi0qj562cxcNi3Bu0upIzrF4aogMc8j92sffof_UbGAqVrv09HVAAt-9zw/exec"

st.title("📡 ShadowSense Real-Time Dashboard")
st.caption("Analyzing edge sensor shadow classifications via Google Sheets backend")

# Setup a sidebar refresh mechanism
st.sidebar.header("Dashboard Controls")
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 10)

# Function to fetch data from your Google Script
def fetch_sensor_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error connecting to Google Sheets API: {e}")
    return pd.DataFrame()

# Fetch latest dataset
df = fetch_sensor_data(API_URL)

if not df.empty:
    # Clean up Timestamp format
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    latest = df.iloc[-1] # Get the absolute latest log entry

    # 1. Summary Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Latest Classification", value=str(latest['label']).upper())
    with col2:
        st.metric(label="Dominance Confidence", value=f"{latest['dom_pct']}%")
    with col3:
        st.metric(label="Temperature", value=f"{latest['temp']} °C")
    with col4:
        st.metric(label="Humidity", value=f"{latest['hum']}%")

    st.markdown("---")

    # 2. Charts Section
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Spectral Metrics Over Time")
        # Melt the dataframe to plot multiple lines (R/B Ratio and Flatness) easily
        chart_data = df.melt(id_vars=['timestamp'], value_vars=['rb', 'flat'], 
                             var_name='Metric', value_name='Value')
        fig_metrics = px.line(chart_data, x='timestamp', y='Value', color='Metric',
                             title="Red/Blue Ratio vs Spectral Flatness",
                             color_discrete_map={'rb': '#EF4444', 'flat': '#3B82F6'})
        st.plotly_chart(fig_metrics, use_container_width=True)

    with right_col:
        st.subheader("Environmental Metrics")
        fig_env = px.line(df, x='timestamp', y='temp', title="Temperature Profile (°C)")
        fig_env.update_traces(line_color='#F59E0B')
        st.plotly_chart(fig_env, use_container_width=True)

    # 3. Raw Data Table View
    st.subheader("Recent Summaries Log")
    st.dataframe(df.sort_values(by='timestamp', ascending=False), use_container_width=True)

else:
    st.warning("Awaiting data from Google Sheets... Is the hardware sending payloads?")

# Auto-refresh loop logic
time.sleep(refresh_rate)
st.rerun()
