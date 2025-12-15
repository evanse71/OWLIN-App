import streamlit as st
import requests
import os
import pandas as pd
import datetime as dt
import altair as alt
from pathlib import Path
from sdk.owlin_agent_sdk import OwlinAgentSDK

BASE_URL = "http://127.0.0.1:8000"
sdk = OwlinAgentSDK(BASE_URL)

st.set_page_config(page_title="Owlin – Upload MVP", layout="wide")
st.title("Owlin – Upload MVP")

# Check for license
license_exists = any(Path("license").glob("*.lic"))

cols = st.columns(3)
with cols[0]:
    if st.button("Health check"):
        st.json(sdk.health())
with cols[1]:
    if st.button("List invoices"):
        st.json(sdk.list_invoices())
with cols[2]:
    doc_id = st.text_input("OCR doc_id", value="1")
    if st.button("Run OCR"):
        st.json(sdk.run_ocr(doc_id))

# Upload & OCR section
with st.expander("Upload & OCR"):
    if not license_exists:
        st.warning("🔒 **Limited Mode**: You need a valid license to upload/parse documents.")
        st.info("Create a file `license/site.lic` to unlock upload functionality.")
    
    uploaded_file = st.file_uploader(
        "Choose invoice or delivery note", 
        type=["pdf", "png", "jpg", "jpeg"],
        disabled=not license_exists
    )
    
    if uploaded_file and license_exists:
        if st.button("Upload File"):
            try:
                # Upload file to backend
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                doc_id = result["doc_id"]
                
                st.success(f"✅ File uploaded successfully!")
                st.info(f"**Document ID:** `{doc_id}`")
                
                # Store doc_id in session state for OCR
                st.session_state.uploaded_doc_id = doc_id
                
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
    
    # OCR section
    if hasattr(st.session_state, 'uploaded_doc_id'):
        st.subheader("Run OCR")
        st.write(f"**Document ID:** `{st.session_state.uploaded_doc_id}`")
        
        if st.button("Run OCR on this doc_id"):
            try:
                result = sdk.run_ocr(st.session_state.uploaded_doc_id)
                st.json(result)
            except Exception as e:
                st.error(f"OCR failed: {str(e)}")

# Recent uploads table
st.subheader("Recent Uploads (last 10)")
try:
    response = requests.get(f"{BASE_URL}/api/documents/recent", timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if data["documents"]:
        st.table(data["documents"])
    else:
        st.info("No documents uploaded yet.")
        
except Exception as e:
    st.error(f"Failed to load recent uploads: {str(e)}")

# Price timeline section
with st.expander("Price timeline (by supplier)"):
    if not license_exists:
        st.warning("🔒 **Limited Mode**: Valid license required for analytics.")
        st.info("Create a file `license/site.lic` to unlock analytics functionality.")
    
    # Fetch suppliers
    try:
        response = requests.get(f"{BASE_URL}/api/analytics/suppliers", timeout=10)
        response.raise_for_status()
        suppliers_data = response.json()
        suppliers_list = suppliers_data.get("suppliers", [])
    except Exception as e:
        st.error(f"Failed to load suppliers: {str(e)}")
        suppliers_list = []
    
    if suppliers_list:
        supplier = st.selectbox("Supplier", suppliers_list, disabled=not license_exists)
    else:
        supplier = st.text_input("Supplier name", value="TestCo", disabled=not license_exists)
    
    # Range selector
    rng_choice = st.selectbox("Time range", ["1M", "3M", "12M", "All"], index=1, disabled=not license_exists)
    
    if st.button("Show timeline", disabled=not license_exists):
        try:
            base = "http://127.0.0.1:8000"
            resp = requests.get(f"{base}/api/analytics/price_history", params={"supplier": supplier}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("series", [])
            
            if not data:
                st.info("No data for this supplier yet.")
            else:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                
                # Range filter
                if rng_choice != "All":
                    months = {"1M": 1, "3M": 3, "12M": 12}[rng_choice]
                    cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=months)
                    df = df[df["date"] >= cutoff]
                
                if len(df) > 0:
                    # Store filtered DataFrame in session state for CSV export
                    st.session_state["timeline_df"] = df
                    
                    chart = alt.Chart(df).mark_line(point=True).encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("value:Q", title="Average price"),
                        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("value:Q", format=".2f")]
                    ).properties(height=260)
                    
                    st.altair_chart(chart, use_container_width=True)
                    st.caption(f"{supplier} · {len(df)} points")
                    
                    # CSV export button
                    csv_data = df.to_csv(index=False)
                    filename = f"timeline_{supplier}_{rng_choice}.csv"
                    st.download_button(
                        "Download CSV",
                        csv_data,
                        filename,
                        "text/csv",
                        key="download_csv"
                    )
                else:
                    st.info(f"No data in the selected {rng_choice} range.")
                    # Clear session state if no data
                    if "timeline_df" in st.session_state:
                        del st.session_state["timeline_df"]
                    
        except Exception as e:
            st.error(f"Timeline error: {e}")

st.caption(f"Backend: {BASE_URL}")