import streamlit as st


def render_invoice_card(invoice: dict) -> tuple[bool, bool]:
    """
    Renders a white invoice card with supplier details, status, progress,
    metadata, and interactive buttons.

    Args:
        invoice (dict): A dictionary containing invoice details with keys:
            - 'id': str (Invoice ID)
            - 'supplier_name': str
            - 'site_name': str
            - 'upload_date': str (e.g., "YYYY-MM-DD")
            - 'status': str (one of "Scanning", "Matched", "No Match", "Issues")
            - 'issue_count': int (optional, only if status is "Issues")
            - 'progress1': float (0.0 to 1.0)
            - 'progress2': float (0.0 to 1.0)
            - 'filename': str
            - 'value': float

    Returns:
        tuple[bool, bool]: A tuple (view_clicked, delete_clicked) indicating
                           if the respective buttons were clicked.
    """
    view_clicked = False
    delete_clicked = False

    # Start the white card container using st.markdown for HTML/CSS
    st.markdown(
        '''<div style="
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 20px;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
        ">''', unsafe_allow_html=True
    )

    # Header Section: Supplier Name, Site Name, Upload Date & Delete Button
    col1_header, col2_delete = st.columns([3, 1])

    with col1_header:
        st.markdown(f"**{invoice['supplier_name']}**")
        st.markdown(f"<span style='font-size: small;'>{invoice['site_name']}</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color: #A9A9A9; font-size: small;'>{invoice['upload_date']}</span>", unsafe_allow_html=True)

    with col2_delete:
        st.write("")  # Spacer
        delete_clicked = st.button("✖", key=f"delete_invoice_{invoice['id']}", help="Delete Invoice")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Status Badge
    status_color = "gray"
    status_icon = "?"
    status_display_text = "Unknown Status"

    if invoice['status'] == "Scanning":
        status_color = "gold"  # Yellow
        status_icon = "●"      # Black Circle
        status_display_text = "Scanning"
    elif invoice['status'] == "Matched":
        status_color = "green"
        status_icon = "✔"      # Heavy Check Mark
        status_display_text = "Matched"
    elif invoice['status'] == "No Match":
        status_color = "red"
        status_icon = "!"      # Exclamation Mark
        status_display_text = "No Match"
    elif invoice['status'] == "Issues":
        status_color = "orange"
        status_icon = "▲"      # Black Up-Pointing Triangle
        issue_count = invoice.get('issue_count', 'X')
        status_display_text = f"{issue_count} Issues"

    st.markdown(
        f"<div style='display: flex; align-items: center; gap: 8px; font-weight: bold; padding-top: 5px; padding-bottom: 5px;'>"
        f"<span style='color: {status_color}; font-size: 1.2em;'>{status_icon}</span>"
        f"<span>{status_display_text}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Progress Bars
    st.progress(invoice['progress1'], text="Invoice Scan")
    st.progress(invoice['progress2'], text="Delivery Note Matching")

    # Metadata Row: Invoice ID, Filename (truncated), Value (£X.XX)
    meta_col1, meta_col2, meta_col3 = st.columns(3)

    with meta_col1:
        st.markdown(f"<span style='font-size: small;'>ID:</span><br><strong>{invoice['id']}</strong>", unsafe_allow_html=True)
    with meta_col2:
        filename = invoice['filename']
        truncated_filename = (filename[:25] + '...') if len(filename) > 28 else filename
        st.markdown(f"<span style='font-size: small;'>File:</span><br><strong>{truncated_filename}</strong>", unsafe_allow_html=True)
    with meta_col3:
        st.markdown(f"<span style='font-size: small;'>Value:</span><br><strong>£{invoice['value']:.2f}</strong>", unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    view_clicked = st.button("View Details", key=f"view_invoice_{invoice['id']}", use_container_width=True)

    # End the white card container
    st.markdown("</div>", unsafe_allow_html=True)

    return view_clicked, delete_clicked 