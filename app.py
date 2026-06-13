import streamlit as st
import pandas as pd
import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Meta Pipeline Dashboard", layout="wide")
st.title("🚀 Meta Pipeline Enterprise Dashboard")
st.markdown("---")

# Inject minimal CSS for link and table styling
st.markdown(
    """
    <style>
    a {
        text-decoration: none;
        color: #464feb;
    }
    tr th, tr td {
        border: 1px solid #e6e6e6;
    }
    tr th {
        background-color: #f5f5f5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar for status
st.sidebar.header("System Status")
st.sidebar.success("Database: Connected (Proxy)")
st.sidebar.info(
    f"Project ID: {os.getenv('INSTANCE_CONNECTION_NAME', 'Unknown').split(':')[0]}"
)

# Main content
col1, col2 = st.columns(2)
with col1:
    st.header("Mission Overview")
    st.write("Track your multi-agent automation missions here.")
    # Placeholder for data
    data = {
        "Mission ID": ["M-101", "M-102", "M-103"],
        "Client": ["Enterprise-777", "SaaS-99", "Vault-X"],
        "Status": ["Completed", "Running", "Failed"],
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
st.markdown("---")
st.header("Run Mission")

# Default to a local dev backend so the UI (upload/trigger) appears during development.
# Override by setting the BACKEND_URL environment variable.
backend_url = os.getenv("BACKEND_URL", "https://meta-pipeline-backend-680132354800.northamerica-northeast2.run.app")

if "BACKEND_URL" not in os.environ:
    st.info(
        f"Connecting to: {backend_url}"
    )

mission_id = st.text_input("Mission ID")
client_id = st.text_input("Client ID")
task_name = st.text_input("Task Name (optional)")

if st.button("Trigger Mission"):
    if not backend_url:
        st.error("Cannot trigger mission because BACKEND_URL is not configured.")
    elif not mission_id or not client_id:
        st.error("Please enter both Mission ID and Client ID.")
    else:
        payload = {
            "mission_id": mission_id,
            "client_id": client_id,
        }
        if task_name:
            payload["task_name"] = task_name
        try:
            response = requests.post(
                f"{backend_url.rstrip('/')}/run-mission",
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            st.success("Mission triggered successfully.")
            st.json(data)
            st.session_state["last_mission_results"] = data.get("results", {})
        except requests.exceptions.RequestException as exc:
            st.error(f"Mission trigger failed: {exc}")

# --- HITL AWARENESS (Moved out of button block for persistence) ---
if "last_mission_results" in st.session_state:
    context = st.session_state["last_mission_results"]
    if context.get("hitl_status") == "awaiting_review":
        st.warning("⚠️ Mission is paused for human review (HITL).")
        
        # Stage 2: Active Verification & Correction Window
        st.markdown("### Mission Context Review")
        st.info("You can review and modify the mission data before resuming.")
        
        # Use a text area for raw JSON editing to ensure precision for nested data
        import json
        context_str = st.text_area(
            "Mission Payload (JSON)", 
            value=json.dumps(context, indent=2),
            height=300
        )
        
        if st.button("✅ Approve & Resume Mission"):
            try:
                updated_context = json.loads(context_str)
                resume_resp = requests.post(
                    f"{backend_url.rstrip('/')}/resume-mission",
                    json={
                        "client_id": client_id, 
                        "context": updated_context,
                        "thread_id": context.get("thread_id")
                    },
                    timeout=20,
                )
                resume_resp.raise_for_status()
                st.success("Mission resumed successfully.")
                st.json(resume_resp.json())
                del st.session_state["last_mission_results"]
            except json.JSONDecodeError:
                st.error("Invalid JSON format in payload.")
            except requests.exceptions.RequestException as e:
                st.error(f"Resume failed: {e}")

# File upload section
st.markdown("---")
st.header("Upload File")
with st.expander("Upload a brief, asset, or CSV"):
    client_name = st.text_input(
        "Client / Company Name",
        placeholder="e.g. Enterprise-777",
        help="Enter the client or company this file belongs to.",
    )
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=["pdf", "csv", "xlsx", "xls", "txt"],
    )
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        st.write("**Filename:**", uploaded_file.name)
        st.write("**Size (bytes):**", len(file_bytes))
        if st.button("Send to backend"):
            if not backend_url:
                st.error("No BACKEND_URL configured; cannot upload to backend.")
            elif not client_name.strip() or client_name.strip().lower() == "string":
                st.error("Please enter a valid Client / Company Name before uploading.")
            else:
                try:
                    files = {"file": (uploaded_file.name, file_bytes)}
                    resp = requests.post(
                        f"{backend_url.rstrip('/')}/upload-file",
                        files=files,
                        data={"client_id": client_name.strip()},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    if not payload.get("success"):
                        st.error(payload.get("message", "Upload failed"))
                        if payload.get("processing") and payload["processing"].get(
                            "errors"
                        ):
                            st.json(payload["processing"]["errors"])
                        else:
                            st.json(payload)
                    else:
                        st.success(
                            f"Upload received for **{client_name.strip()}**; processing started."
                        )
                        st.json(payload)
                        job_id = (payload.get("job") or {}).get("job_id")
                        if job_id:
                            status_placeholder = st.empty()
                            max_checks = 240 # Increased polling for longer agent chains
                            for _ in range(max_checks):
                                r2 = requests.get(
                                    f"{backend_url.rstrip('/')}/upload-status/{job_id}",
                                    timeout=30,
                                )
                                r2.raise_for_status()
                                s = r2.json()
                                job_data = s.get("job") or {}
                                status = job_data.get("status")
                                status_placeholder.json(s)
                                if status in ("COMPLETED", "FAILED"):
                                    break
                                time.sleep(1)
                            else:
                                st.warning(
                                    "Polling stopped after timeout. Backend may still be processing."
                                )
                except requests.exceptions.RequestException as e:
                    st.error(f"Upload failed: {e}")
