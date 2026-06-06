# File upload section
st.markdown("---")
st.header("Upload File")
with st.expander("Upload a brief, asset, or CSV"):
    client_name = st.text_input(
        "Client / Company Name",
        placeholder="e.g. Enterprise-777",
        help="Enter the client or company this file belongs to."
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
                        timeout=120
                    )
                    resp.raise_for_status()
                    payload = resp.json()

                    if not payload.get("success"):
                        st.error(payload.get("message", "Upload failed"))
                        if payload.get("processing") and payload["processing"].get("errors"):
                            st.json(payload["processing"]["errors"])
                        else:
                            st.json(payload)
                    else:
                        st.success(f"Upload received for **{client_name.strip()}**; processing started.")
                        st.json(payload)

                        job_id = (payload.get("job") or {}).get("job_id")
                        if job_id:
                            import time
                            status_placeholder = st.empty()
                            while True:
                                r2 = requests.get(f"{backend_url.rstrip('/')}/upload-status/{job_id}", timeout=30)
                                r2.raise_for_status()
                                s = r2.json()
                                status_placeholder.json(s)
                                if (s.get("job") or {}).get("status") in ("completed", "failed"):
                                    break
                                time.sleep(1)

                except requests.exceptions.RequestException as e:
                    st.error(f"Upload failed: {e}")
