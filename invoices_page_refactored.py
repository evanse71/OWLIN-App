import streamlit as st
import time
import random

# Mock database of uploaded files
if "invoices" not in st.session_state:
    st.session_state.invoices = []

# --- Improved Upload Area ---
def render_upload_area():
    st.markdown("""
    <div style='background: #F8FAFC; border: 1.5px solid #E5E7EB; border-radius: 18px; padding: 2.2rem 2.5rem 1.5rem 2.5rem; margin-bottom: 2.2rem; box-shadow: 0 2px 8px rgba(60,60,60,0.04);'>
      <div style='display: flex; flex-wrap: wrap; gap: 2.5rem; align-items: flex-end;'>
        <div style='flex: 1 1 320px;'>
          <div style='font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>Invoice PDF <span style="color:#E04545">*</span></div>
          <div style='margin-bottom: 0.5rem;'>
            <!-- Invoice uploader -->
            </div>
        </div>
        <div style='flex: 1 1 320px;'>
          <div style='font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>Delivery Note (Optional)</div>
          <div style='margin-bottom: 0.5rem;'>
            <!-- Delivery uploader -->
          </div>
        </div>
        <div style='flex: 0 0 220px;'>
          <div style='margin-bottom: 0.7rem;'></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 3, 2])
    with col1:
        invoice_file = st.file_uploader("", type=["pdf"], key="invoice_upload", label_visibility="collapsed")
    with col2:
        delivery_file = st.file_uploader("", type=["pdf"], key="delivery_upload", label_visibility="collapsed")
    with col3:
        st.selectbox("🏨 Select Venue", ["All Venues", "Main Kitchen", "Rooftop", "Cellar"], key="venue_picker")
        st.toggle("Show Mismatches Only", key="mismatch_toggle")
    return invoice_file, delivery_file

def simulate_invoice_scan(invoice_file):
    """Fake scanning logic for now"""
    with st.spinner("Scanning invoice for details..."):
        time.sleep(2)
    return {
        "supplier": random.choice(["Blas ar Bwyd", "Fresh Catch Co", "Garden Fresh Supplies"]),
        "invoice_id": f"#INV{random.randint(1000, 9999)}",
        "date": "2025-07-08",
        "total": f"£{random.randint(200, 1200)}"
    }

def simulate_delivery_pairing():
    time.sleep(1.5)
    return random.choice([True, False])

def render_invoice_card(invoice):
    with st.container():
        st.markdown("---")
        st.markdown(f"#### 📄 {invoice['file'].name}")
        st.caption(f"Size: {invoice['file'].size / 1024:.1f} KB")

        if invoice["status"] == "scanning":
            st.progress(35, text="📊 Uploading...")
            time.sleep(1.2)
            st.progress(80, text="🔍 Scanning for invoice data...")
            invoice["meta"] = simulate_invoice_scan(invoice["file"])
            invoice["status"] = "scanned"
            st.rerun()

        if invoice["status"] == "scanned":
            meta = invoice["meta"]
            st.success("✅ Invoice scanned successfully.")
            st.markdown(f"""
            - **Supplier:** {meta['supplier']}
            - **Invoice ID:** {meta['invoice_id']}
            - **Date:** {meta['date']}
            - **Total:** {meta['total']}
            """)

            st.info("🔄 Attempting to match with delivery note...")
            matched = simulate_delivery_pairing()
            invoice["delivery_matched"] = matched
            invoice["status"] = "matched"
            st.rerun()

        if invoice["status"] == "matched":
            meta = invoice["meta"]
            st.markdown(f"""
            - **Supplier:** {meta['supplier']}
            - **Invoice ID:** {meta['invoice_id']}
            - **Date:** {meta['date']}
            - **Total:** {meta['total']}
            """)
            if invoice["delivery_matched"]:
                st.success("✓ Delivery Note Paired")
            else:
                st.warning("❌ No Delivery Note Found Yet")

            st.button("✅ Submit Invoice", key=f"submit_{meta['invoice_id']}")

def render_invoices_page():
    st.title("📑 Invoice Review")

    st.markdown("### 1. Upload Invoice and Delivery Note")
    invoice_file, delivery_file = render_upload_area()

    if invoice_file is not None:
        st.success(f"Uploaded: {invoice_file.name} ({invoice_file.size/1024:.1f} KB)")
        st.session_state.invoices.append({
            "file": invoice_file,
            "status": "scanning",
            "meta": None,
            "delivery_matched": None
        })
        st.rerun()

    st.markdown("---")
    st.markdown("### 2. Invoice Cards")

    if not st.session_state.invoices:
        st.info("Upload an invoice to begin.")
    else:
        st.markdown('''
            <div style="text-align: center; padding: 3rem 1rem; color: #666;">
                No invoices uploaded yet.
            </div>
        ''', unsafe_allow_html=True)

def format_currency(amount):
    """
    Format currency consistently with proper locale and error handling.
    Args:
        amount (float/int): Amount to format
    Returns:
        str: Formatted currency string
    """
    try:
        if amount is None:
            return '£0.00'
        # Convert to float and handle edge cases
        amount = float(amount)
        if amount < 0:
            return f'-£{abs(amount):,.2f}'
        else:
            return f'£{amount:,.2f}'
    except (ValueError, TypeError):
        return '£0.00'

if __name__ == "__main__":
    render_invoices_page() 