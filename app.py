import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Meta Pipeline Dashboard", layout="wide")

st.title("🚀 Meta Pipeline Enterprise Dashboard")
st.markdown("---")

# Sidebar for status
st.sidebar.header("System Status")
st.sidebar.success("Database: Connected (Proxy)")
st.sidebar.info(f"Project ID: {os.getenv('INSTANCE_CONNECTION_NAME', 'Unknown').split(':')[0]}")

# Main content
col1, col2 = st.columns(2)

with col1:
    st.header("Mission Overview")
    st.write("Track your multi-agent automation missions here.")
    # Placeholder for data
    data = {
        "Mission ID": ["M-101", "M-102", "M-103"],
        "Client": ["Enterprise-777", "SaaS-99", "Vault-X"],
        "Status": ["Completed", "Running", "Failed"]
    }
    df = pd.DataFrame(data)
    st.table(df)

with col2:
    st.header("System Metrics")
    st.metric(label="Total Missions", value=42, delta=3)
    st.metric(label="Success Rate", value="95%", delta="2%")

st.markdown("---")
st.subheader("Live Logs")
st.code("Initializing agents...\nBridge established.\nMission M-102 started.")
