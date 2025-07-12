import streamlit as st
import datetime

# You may want to import theme colors from app.theme if available
# from app.theme import COLORS, FONTS

def render_upload_boxes():
    """
    Renders two side-by-side glass-style upload boxes for invoices and delivery notes.
    Handles file uploads and saves them to session state.
    """
    # Initialize session state lists if not present
    if "uploaded_invoices" not in st.session_state:
        st.session_state["uploaded_invoices"] = []
    if "uploaded_delivery_notes" not in st.session_state:
        st.session_state["uploaded_delivery_notes"] = []

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
        <div class="owlin-glass-box" style="background: rgba(255,255,255,0.25); border-radius: 20px; padding: 30px; box-shadow: 0 4px 24px rgba(60,60,60,0.08); border: 1.5px solid rgba(200,200,200,0.25); backdrop-filter: blur(6px); transition: 0.2s;">
            <div style="font-size:1.15rem;font-weight:600;margin-bottom:1rem;letter-spacing:0.01em;">Upload Invoice</div>
        </div>
        """, unsafe_allow_html=True)
        invoice_files = st.file_uploader(
            "",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="invoice_upload_box",
            label_visibility="collapsed"
        )
        if invoice_files:
            for file in invoice_files:
                # Only add new files (avoid duplicates)
                if file not in st.session_state["uploaded_invoices"]:
                    st.session_state["uploaded_invoices"].append({
                        "file": file,
                        "timestamp": datetime.datetime.now()
                    })
            st.markdown(f"<div style='margin-top:0.7em;font-size:0.97rem;color:#20513A;font-weight:500;'>📄 {len(invoice_files)} file(s) uploaded</div>", unsafe_allow_html=True)
            for entry in st.session_state["uploaded_invoices"]:
                st.markdown(f"<div style='font-size:0.95rem;margin-bottom:0.2em;'>• {entry['file'].name} <span style='color:#888;font-size:0.88em;'>({entry['timestamp'].strftime('%H:%M:%S')})</span></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="owlin-glass-box" style="background: rgba(255,255,255,0.22); border-radius: 20px; padding: 30px; box-shadow: 0 4px 24px rgba(60,60,60,0.08); border: 1.5px solid rgba(200,200,200,0.22); backdrop-filter: blur(6px); transition: 0.2s;">
            <div style="font-size:1.15rem;font-weight:600;margin-bottom:1rem;letter-spacing:0.01em;">Upload Delivery Note</div>
        </div>
        """, unsafe_allow_html=True)
        delivery_files = st.file_uploader(
            "",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="delivery_upload_box",
            label_visibility="collapsed"
        )
        if delivery_files:
            for file in delivery_files:
                if file not in st.session_state["uploaded_delivery_notes"]:
                    st.session_state["uploaded_delivery_notes"].append({
                        "file": file,
                        "timestamp": datetime.datetime.now()
                    })
            st.markdown(f"<div style='margin-top:0.7em;font-size:0.97rem;color:#20513A;font-weight:500;'>📎 {len(delivery_files)} file(s) uploaded</div>", unsafe_allow_html=True)
            for entry in st.session_state["uploaded_delivery_notes"]:
                st.markdown(f"<div style='font-size:0.95rem;margin-bottom:0.2em;'>• {entry['file'].name} <span style='color:#888;font-size:0.88em;'>({entry['timestamp'].strftime('%H:%M:%S')})</span></div>", unsafe_allow_html=True) 