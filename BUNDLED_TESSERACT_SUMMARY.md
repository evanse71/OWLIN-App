import streamlit as st
from io import BytesIO
import pandas as pd
from app.invoices_page import render_invoices_page

# --- Custom CSS for Owlin Brand and Responsive Layout ---
st.markdown('''
    <style>
    body, .stApp {
        background: #f5f6fa !important;
    }
    .owlin-box {
        background: #fff !important;
        border-radius: 18px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
        padding: 2.2rem 2rem 2rem 2rem !important;
        margin-bottom: 2.2rem !important;
    }
    .owlin-heading {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: #222222 !important;
        margin-bottom: 2.2rem !important;
        letter-spacing: -1px;
    }
    .owlin-upload-col {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        justify-content: flex-start;
        height: 100%;
    }
    .owlin-upload-box {
        background: #fff !important;
        border-radius: 18px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
        padding: 2.5rem 2rem 2.5rem 2rem !important;
        min-height: 260px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 0;
    }
    .owlin-upload-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #222222;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .owlin-upload-subtitle {
        font-size: 1rem;
        color: #888;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .owlin-upload-area {
        width: 100%;
        min-height: 140px;
        background: #f5f6fa !important;
        border-radius: 14px !important;
        border: 2.5px dashed #d1d5db !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2.5rem 0 !important;
        margin-bottom: 0.5rem;
        position: relative;
    }
    .owlin-upload-area .cloud-icon {
        font-size: 2.5rem;
        color: #b3b3b3;
        margin-bottom: 0.5rem;
    }
    .owlin-upload-area .upload-text {
        font-size: 1.08rem;
        color: #888;
        margin-bottom: 0.5rem;
    }
    .owlin-upload-area .browse-btn {
        background: #f1c232;
        color: #222;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.7rem 1.5rem;
        font-size: 1.01rem;
        cursor: pointer;
        margin-top: 0.5rem;
        transition: background 0.18s;
    }
    .owlin-upload-area .browse-btn:hover {
        background: #e6a93a;
    }
    .owlin-collapsible-box {
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-top: 1.5rem;
        margin-bottom: 2rem;
        padding: 0;
    }
    .owlin-invoice-main-flex {
        display: flex;
        flex-direction: row;
        background: #fff;
        border-radius: 14px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        min-height: 520px;
        margin-bottom: 0.5rem;
        overflow: hidden;
    }
    .owlin-invoice-list-sidebar {
        background: #e9ecef;
        border-radius: 14px 0 0 14px;
        min-width: 260px;
        max-width: 320px;
        height: 520px;
        overflow-y: auto;
        padding: 1.2rem 0.5rem 1.2rem 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .owlin-invoice-card {
        background: #fff;
        border-radius: 10px;
        margin-bottom: 1.1rem;
        padding: 1.1rem 1.1rem 0.8rem 1.1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        cursor: pointer;
        border: 2px solid transparent;
        transition: border 0.18s, box-shadow 0.18s;
    }
    .owlin-invoice-card.selected, .owlin-invoice-card:hover {
        border: 2.5px solid #222222;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .owlin-invoice-status-icon {
        font-size: 1.2rem;
        margin-right: 0.7rem;
        vertical-align: middle;
    }
    .owlin-invoice-status-matched { color: #4CAF50; }
    .owlin-invoice-status-discrepancy { color: #f1c232; }
    .owlin-invoice-status-not_paired { color: #ff3b30; }
    .owlin-invoice-list-title {
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 1.2rem;
        color: #222222;
    }
    .owlin-invoice-details-pane {
        background: #fff;
        border-radius: 0 14px 14px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        padding: 2.2rem 2.2rem 1.5rem 2.2rem;
        height: 520px;
        overflow-y: auto;
        position: relative;
        scrollbar-width: thin;
        scrollbar-color: #d1d5db #f5f6fa;
    }
    .owlin-invoice-details-pane::-webkit-scrollbar {
        width: 8px;
        background: #f5f6fa;
    }
    .owlin-invoice-details-pane::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 6px;
    }
    .owlin-invoice-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-bottom: 1.2rem;
    }
    .owlin-invoice-table th {
        background: #f5f6fa;
        font-weight: 700;
        padding: 0.7rem 0.6rem;
        border-bottom: 2px solid #e9ecef;
        font-size: 1rem;
    }
    .owlin-invoice-table td {
        padding: 0.7rem 0.6rem;
        font-size: 0.98rem;
        border-bottom: 1px solid #f0f0f0;
    }
    .owlin-discrepancy-cell {
        background: #fffbe6 !important;
        color: #b8860b !important;
        font-weight: 600;
        border-radius: 6px;
        position: relative;
    }
    .owlin-discrepancy-icon {
        color: #f1c232;
        font-size: 1.1rem;
        margin-left: 0.3rem;
        vertical-align: middle;
    }
    .owlin-invoice-total-row td {
        font-weight: 700;
        font-size: 1.08rem;
        border-bottom: none;
        padding-top: 1.2rem;
    }
    .owlin-flagged-issues-box {
        background: #f9e5b7;
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        margin: 1.2rem 0 1.7rem 0;
        color: #222;
        font-size: 1rem;
        border: 1px solid #f1c232;
    }
    .owlin-flagged-issue-label {
        font-weight: 700;
        color: #b8860b;
        margin-right: 0.7rem;
    }
    .owlin-flagged-issue-amount {
        font-weight: 700;
        color: #b8860b;
        margin-left: 0.7rem;
    }
    .owlin-invoice-action-row {
        display: flex;
        gap: 1.1rem;
        margin-top: 0.7rem;
    }
    .owlin-edit-invoice-btn, .owlin-pair-delivery-btn {
        background: #f1c232;
        color: #222;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.85rem 2.1rem;
        font-size: 1.05rem;
        cursor: pointer;
        margin-right: 0.5rem;
        transition: background 0.18s;
    }
    .owlin-edit-invoice-btn:hover, .owlin-pair-delivery-btn:hover {
        background: #e6a93a;
    }
    .owlin-submit-owlin-btn {
        background: #222222;
        color: #fff;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.85rem 2.1rem;
        font-size: 1.05rem;
        cursor: pointer;
        transition: background 0.18s;
    }
    .owlin-submit-owlin-btn:hover {
        background: #000;
    }
    @media (max-width: 1100px) {
        .owlin-invoice-main-flex {
            flex-direction: column;
        }
        .owlin-invoice-list-sidebar, .owlin-invoice-details-pane {
            max-width: 100%;
            min-width: 0;
            border-radius: 14px 14px 0 0;
            height: auto;
        }
    }
    @media (max-width: 800px) {
        .owlin-box, .owlin-collapsible-box {
            padding: 1.2rem 0.5rem !important;
        }
        .owlin-invoice-details-pane {
            padding: 1.2rem 0.5rem 1rem 0.5rem;
        }
        .owlin-upload-box {
            padding: 1.2rem 0.5rem 1.2rem 0.5rem !important;
        }
    }
    </style>
''', unsafe_allow_html=True)

# --- Main Title ---
st.markdown("<div class='owlin-heading'>Invoices</div>", unsafe_allow_html=True)

# --- Upload Section (Modern, Accessible, Mockup-Accurate) ---
st.markdown('''
    <style>
    .owlin-upload-row {
        display: flex;
        gap: 2.5rem;
        margin-bottom: 2.5rem;
    }
    @media (max-width: 900px) {
        .owlin-upload-row { flex-direction: column; gap: 1.5rem; }
    }
    .owlin-upload-box-modern {
        background: #fff;
        border-radius: 22px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        flex: 1 1 0;
        min-width: 0;
        padding: 2.5rem 2rem 2rem 2rem;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        justify-content: flex-start;
        width: 100%;
    }
    .owlin-upload-heading {
        font-size: 1.35rem;
        font-weight: 800;
        color: #222;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
        text-align: left;
    }
    .owlin-upload-subheading {
        font-size: 1.01rem;
        color: #666;
        margin-bottom: 1.5rem;
        text-align: left;
    }
    .owlin-dragdrop-area {
        border: 2.5px dashed #d1d5db;
        border-radius: 14px;
        background: #f5f6fa;
        min-height: 150px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: border-color 0.2s;
        position: relative;
        margin-bottom: 1.2rem;
    }
    .owlin-dragdrop-area:hover, .owlin-dragdrop-area:focus-within {
        border-color: #b3b3b3;
    }
    .owlin-cloud-icon {
        font-size: 2.7rem;
        color: #b3b3b3;
        margin-bottom: 0.5rem;
    }
    .owlin-dragdrop-text {
        font-size: 1.08rem;
        color: #888;
        margin-bottom: 0.2rem;
    }
    .owlin-uploaded-list {
        margin: 0;
        padding: 0;
        list-style: none;
    }
    .owlin-uploaded-list li {
        font-size: 1.01rem;
        color: #333;
        background: #f5f6fa;
        border-radius: 7px;
        margin-bottom: 0.4rem;
        padding: 0.5rem 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .owlin-uploaded-filename {
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 70vw;
    }
    .owlin-uploaded-size {
        color: #888;
        font-size: 0.97rem;
        margin-left: 1.2rem;
    }
    </style>
''', unsafe_allow_html=True)

st.markdown('<div class="owlin-upload-row">', unsafe_allow_html=True)

# --- Upload Invoices Box ---
st.markdown('<div class="owlin-upload-box-modern">', unsafe_allow_html=True)
st.markdown('<div class="owlin-upload-heading">+Upload Invoices</div>', unsafe_allow_html=True)
st.markdown('<div class="owlin-upload-subheading">Accepted formats: PDF, JPG, JPEG, PNG, ZIP<br><span style="color:#444;">Phone Photos supported (JPG, JPEG, PNG)</span></div>', unsafe_allow_html=True)
uploaded_invoices = st.file_uploader(
    "Upload Invoices",
    type=["pdf", "jpg", "jpeg", "png", "zip"],
    accept_multiple_files=True,
    key="upload_invoices_modern",
    label_visibility="collapsed",
)
st.markdown(
    f'''<label for="upload_invoices_modern" class="owlin-dragdrop-area" tabindex="0" aria-label="Upload Invoices">
        <span class="owlin-cloud-icon">☁️</span>
        <span class="owlin-dragdrop-text">Drag and drop files here or click to browse</span>
    </label>''',
    unsafe_allow_html=True
)
# Uploaded files list
if uploaded_invoices:
    st.markdown('<ul class="owlin-uploaded-list">', unsafe_allow_html=True)
    for f in uploaded_invoices:
        size_kb = f"{f.size/1024:.1f} KB" if f.size < 1024*1024 else f"{f.size/1024/1024:.2f} MB"
        st.markdown(f'<li><span class="owlin-uploaded-filename">{f.name}</span><span class="owlin-uploaded-size">{size_kb}</span></li>', unsafe_allow_html=True)
    st.markdown('</ul>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Upload Delivery Notes Box ---
st.markdown('<div class="owlin-upload-box-modern">', unsafe_allow_html=True)
st.markdown('<div class="owlin-upload-heading">+Upload Delivery Notes</div>', unsafe_allow_html=True)
st.markdown('<div class="owlin-upload-subheading">Accepted formats: PDF, JPG, JPEG, PNG, ZIP<br><span style="color:#444;">Phone Photos supported (JPG, JPEG, PNG)</span></div>', unsafe_allow_html=True)
uploaded_delivery_notes = st.file_uploader(
    "Upload Delivery Notes",
    type=["pdf", "jpg", "jpeg", "png", "zip"],
    accept_multiple_files=True,
    key="upload_delivery_notes_modern",
    label_visibility="collapsed",
)
st.markdown(
    f'''<label for="upload_delivery_notes_modern" class="owlin-dragdrop-area" tabindex="0" aria-label="Upload Delivery Notes">
        <span class="owlin-cloud-icon">☁️</span>
        <span class="owlin-dragdrop-text">Drag and drop files here or click to browse</span>
    </label>''',
    unsafe_allow_html=True
)
# Uploaded files list
if uploaded_delivery_notes:
    st.markdown('<ul class="owlin-uploaded-list">', unsafe_allow_html=True)
    for f in uploaded_delivery_notes:
        size_kb = f"{f.size/1024:.1f} KB" if f.size < 1024*1024 else f"{f.size/1024/1024:.2f} MB"
        st.markdown(f'<li><span class="owlin-uploaded-filename">{f.name}</span><span class="owlin-uploaded-size">{size_kb}</span></li>', unsafe_allow_html=True)
    st.markdown('</ul>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- Collapsible Invoice List/Details ---
with st.expander("View Invoices Uploaded", expanded=False):
    st.markdown('<div class="owlin-invoice-main-flex">', unsafe_allow_html=True)
    # Sidebar (mock data)
    st.markdown('<div class="owlin-invoice-list-sidebar">', unsafe_allow_html=True)
    st.markdown('<div class="owlin-invoice-list-title">Invoices</div>', unsafe_allow_html=True)
    # Example invoice list (replace with backend data)
    invoices = [
        {"id": "INV-001", "date": "2024-01-15", "supplier": "Blas ar Bwyd", "total": 234.50, "status": "matched"},
        {"id": "INV-002", "date": "2024-01-16", "supplier": "Fresh Foods Ltd", "total": 156.75, "status": "discrepancy"},
        {"id": "INV-003", "date": "2024-01-17", "supplier": "Quality Meats", "total": 89.25, "status": "not_paired"}
    ]
    if 'selected_invoice_idx' not in st.session_state:
        st.session_state.selected_invoice_idx = 0
    for idx, inv in enumerate(invoices):
        status_icon = {
            "matched": '<span class="owlin-invoice-status-icon owlin-invoice-status-matched">✔️</span>',
            "discrepancy": '<span class="owlin-invoice-status-icon owlin-invoice-status-discrepancy">⚠️</span>',
            "not_paired": '<span class="owlin-invoice-status-icon owlin-invoice-status-not_paired">❌</span>'
        }[inv["status"]]
        selected = (idx == st.session_state.selected_invoice_idx)
        card_class = "owlin-invoice-card selected" if selected else "owlin-invoice-card"
        if st.button(f"{inv['id']} - {inv['supplier']} - {inv['date']}", key=f"invoice_card_{idx}"):
            st.session_state.selected_invoice_idx = idx
        st.markdown(f'''<div class="{card_class}">
            {status_icon}
            <b>{inv['id']}</b><br>
            <span style='font-size:0.97rem;color:#555;'>{inv['date']}<br>{inv['supplier']}</span><br>
            <span style='font-size:1.08rem;font-weight:700;color:#222;'>£{inv['total']:.2f}</span>
        </div>''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    # Details pane (mock data)
    st.markdown('<div class="owlin-invoice-details-pane">', unsafe_allow_html=True)
    inv = invoices[st.session_state.selected_invoice_idx]
    st.markdown(f"<div style='font-size:1.25rem;font-weight:700;margin-bottom:0.7rem;'>Invoice: {inv['id']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#888;font-size:1.05rem;margin-bottom:0.7rem;'>Supplier: <b>{inv['supplier']}</b> &nbsp; | &nbsp; Date: {inv['date']}</div>", unsafe_allow_html=True)
    # Example invoice items (replace with backend data)
    items = [
        {"item": "Pork Shoulder", "invoice_qty": 50, "delivery_qty": 45, "unit_price": 5.00, "total": 225.00, "discrepancy": True},
        {"item": "Beef Mince", "invoice_qty": 20, "delivery_qty": 20, "unit_price": 8.75, "total": 175.00, "discrepancy": False},
        {"item": "Salmon Fillets", "invoice_qty": 8, "delivery_qty": 8, "unit_price": 12.00, "total": 96.00, "discrepancy": False}
    ]
    st.markdown('<table class="owlin-invoice-table">', unsafe_allow_html=True)
    st.markdown('<tr><th>Item</th><th>Invoice Qty</th><th>Delivery Qty</th><th>Unit Price (£)</th><th>Total (£)</th></tr>', unsafe_allow_html=True)
    for item in items:
        dq = item['delivery_qty'] if item['delivery_qty'] is not None else '-'
        dq_cell = f"<td>{dq}</td>"
        if item['discrepancy']:
            dq_cell = f"<td class='owlin-discrepancy-cell'>{dq} <span class='owlin-discrepancy-icon'>⚠️</span></td>"
        st.markdown(f"<tr><td>{item['item']}</td><td>{item['invoice_qty']}</td>{dq_cell}<td>£{item['unit_price']:.2f}</td><td>£{item['total']:.2f}</td></tr>", unsafe_allow_html=True)
    st.markdown(f'<tr class="owlin-invoice-total-row"><td colspan="4" style="text-align:right;">Total:</td><td>£{inv["total"]:.2f}</td></tr>', unsafe_allow_html=True)
    st.markdown('</table>', unsafe_allow_html=True)
    # Example flagged issues (replace with backend data)
    flagged_issues = [
        {"label": "2 units missing", "desc": "Potentially Overpaid by £3.50 p/unit", "amount": 7.00},
        {"label": "Missing Delivery note", "desc": "Potential Discrepancy", "amount": 28.00}
    ]
    if flagged_issues:
        st.markdown('<div class="owlin-flagged-issues-box">', unsafe_allow_html=True)
        for issue in flagged_issues:
            st.markdown(f"<span class='owlin-flagged-issue-label'>⚠️ {issue['label']}</span> <span style='color:#555;'>{issue['desc']}</span> <span class='owlin-flagged-issue-amount'>| £{issue['amount']:.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="owlin-invoice-action-row">', unsafe_allow_html=True)
    st.markdown('<button class="owlin-edit-invoice-btn">Edit Invoice</button>', unsafe_allow_html=True)
    st.markdown('<button class="owlin-submit-owlin-btn">Submit to Owlin</button>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Submission Confirmation Box (mockup) ---
st.markdown('<div class="owlin-box" style="max-width:480px;">', unsafe_allow_html=True)
st.markdown('<div style="display:flex;align-items:center;font-size:1.45rem;font-weight:700;margin-bottom:1.1rem;"><span style="font-size:2.5rem;margin-right:1.1rem;color:#4CAF50;">✔️</span> Submission Complete</div>', unsafe_allow_html=True)
st.markdown('''<div style="font-size:1.08rem;margin-bottom:1.2rem;color:#222222;"><ul style='margin:0 0 0 1.2rem;padding:0;'><li><b>12</b> Invoices Submitted</li><li><b>2</b> Issues Flagged and sent for resolution</li><li><b>11</b> Delivery Notes Paired</li><li><b>1</b> Invoice waiting for auto Pairing</li><li>Estimated savings: <b>£85.64</b></li></ul></div>''', unsafe_allow_html=True)
st.markdown('<div style="display:flex;gap:1.1rem;margin-top:0.7rem;">', unsafe_allow_html=True)
st.markdown('<button class="summary-btn-outline" style="background:#fff;color:#222;border:2px solid #222;border-radius:8px;padding:0.85rem 2.1rem;font-size:1.05rem;font-weight:700;cursor:pointer;margin-right:0.5rem;">View Summary Report</button>', unsafe_allow_html=True)
st.markdown('<button class="summary-btn-dark" style="background:#222222;color:#fff;border:none;border-radius:8px;padding:0.85rem 2.1rem;font-size:1.05rem;font-weight:700;cursor:pointer;">View Updates</button>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Invoices Not Paired Section (mockup) ---
st.markdown('<div class="owlin-box">', unsafe_allow_html=True)
st.markdown('<div style="font-size:1.18rem;font-weight:700;margin-bottom:1.2rem;color:#222222;">Invoices Not Paired</div>', unsafe_allow_html=True)
not_paired_invoices = [
    {"id": "INV-003", "date": "2024-01-17", "supplier": "Quality Meats", "total": 89.25}
]
for inv in not_paired_invoices:
    st.markdown('<div style="background:#f5f6fa;border-radius:10px;margin-bottom:1.1rem;padding:1.1rem 1.1rem 0.8rem 1.1rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);display:flex;align-items:center;justify-content:space-between;">', unsafe_allow_html=True)
    st.markdown(f'''<div style="display:flex;align-items:center;"><span style="font-size:1.2rem;color:#ff3b30;margin-right:0.7rem;">❌</span><b>{inv['id']}</b> &nbsp; | &nbsp; {inv['supplier']} &nbsp; | &nbsp; {inv['date']} &nbsp; | &nbsp; <span style='font-weight:700;color:#222;'>£{inv['total']:.2f}</span></div>''', unsafe_allow_html=True)
    st.markdown('<div style="display:flex;gap:0.7rem;">', unsafe_allow_html=True)
    st.markdown('<button class="owlin-edit-invoice-btn">Edit Invoice</button>', unsafe_allow_html=True)
    pair_key = f"pair_delivery_{inv['id']}"
    if st.button("Pair Delivery Note", key=pair_key):
        st.session_state[f"show_pair_dialog_{inv['id']}"] = True
    st.markdown('<button class="owlin-pair-delivery-btn">Pair Delivery Note</button>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    # Dialog for pairing delivery note
    if st.session_state.get(f"show_pair_dialog_{inv['id']}", False):
        st.markdown(f"<div style='background:#fffbe6;border:2px solid #f1c232;padding:2rem 2rem 1.5rem 2rem;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin:1.2rem 0;'>", unsafe_allow_html=True)
        st.markdown(f"<b>Pair Delivery Note for Invoice {inv['id']}</b>", unsafe_allow_html=True)
        uploaded_note = st.file_uploader("Upload or select delivery note", type=["pdf", "jpg", "jpeg", "png", "zip"], key=f"pair_upload_{inv['id']}")
        if st.button("Confirm Pairing", key=f"confirm_pair_{inv['id']}"):
            # TODO: Backend integration for pairing
            st.success(f"Delivery note paired for invoice {inv['id']}!")
            st.session_state[f"show_pair_dialog_{inv['id']}"] = False
        if st.button("Cancel", key=f"cancel_pair_{inv['id']}"):
            st.session_state[f"show_pair_dialog_{inv['id']}"] = False
        st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True) 