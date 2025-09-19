"""
Enhanced Invoices Page for Owlin App
Implements the complete invoices domain with split layout, real data, and full functionality.
"""
import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import os
import json

from app.database import (
    load_invoices_from_db, get_invoice_details, get_issues_for_invoice,
    get_pairing_suggestions, resolve_issue, escalate_issue, 
    confirm_pairing, reject_pairing, get_flagged_issues
)
from app.enhanced_file_processor import (
    save_file_to_disk, save_file_metadata, process_uploaded_file, retry_ocr_for_invoice
)
from app.db_migrations import run_migrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
run_migrations()

def get_user_role():
    """Get current user role - simplified for demo."""
    # In a real implementation, this would get the user role from session/auth
    return st.session_state.get('user_role', 'Finance')

def check_license_status():
    """Check if license allows full functionality."""
    # In a real implementation, this would check the actual license
    return st.session_state.get('license_status', 'full')  # 'full' or 'limited'

def format_currency(pennies: int) -> str:
    """Format currency from pennies to display format."""
    if pennies is None:
        return "£0.00"
    return f"£{pennies / 100:.2f}"

def format_confidence(confidence: float) -> str:
    """Format confidence score for display."""
    if confidence is None:
        return "Unknown"
    return f"{confidence:.1f}%"

def get_status_badge_color(status: str) -> str:
    """Get badge color for status."""
    colors = {
        'pending': 'orange',
        'matched': 'green',
        'discrepancy': 'red',
        'not_paired': 'blue',
        'completed': 'green',
        'failed': 'red'
    }
    return colors.get(status, 'gray')

def get_severity_badge_color(severity: str) -> str:
    """Get badge color for issue severity."""
    colors = {
        'low': 'green',
        'medium': 'orange',
        'high': 'red'
    }
    return colors.get(severity, 'gray')

def render_upload_panel():
    """Render the upload panel."""
    st.subheader("📤 Upload Invoices")
    
    # Check license status
    license_status = check_license_status()
    if license_status == 'limited':
        st.warning("⚠️ Limited Mode: Upload functionality is restricted. Please upgrade your license.")
        return
    
    # Check user role
    user_role = get_user_role()
    if user_role not in ['GM', 'Finance']:
        st.error("❌ Access denied: Only GM and Finance roles can upload invoices.")
        return
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose invoice files",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Upload PDF, PNG, or JPG files containing invoices"
    )
    
    if uploaded_files:
        if st.button("🚀 Process Files", type="primary"):
            process_files(uploaded_files)

def process_files(uploaded_files):
    """Process uploaded files."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = {
        'successful': [],
        'failed': [],
        'total_processed': 0
    }
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"Processing {uploaded_file.name}...")
            
            # Save file to disk
            file_id = save_file_to_disk(uploaded_file, 'invoice')
            
            # Save metadata
            save_file_metadata(
                file_id, uploaded_file.name, 'invoice',
                f"data/uploads/invoices/{file_id}{os.path.splitext(uploaded_file.name)[1]}",
                uploaded_file.size
            )
            
            # Process file
            result = process_uploaded_file(file_id, 'invoice')
            
            if result['success']:
                results['successful'].extend(result['invoice_ids'])
                st.success(f"✅ {uploaded_file.name} processed successfully")
            else:
                results['failed'].append(uploaded_file.name)
                st.error(f"❌ {uploaded_file.name} failed: {result['error']}")
            
            results['total_processed'] += 1
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        except Exception as e:
            logger.error(f"Failed to process {uploaded_file.name}: {e}")
            results['failed'].append(uploaded_file.name)
            st.error(f"❌ {uploaded_file.name} failed: {str(e)}")
            results['total_processed'] += 1
    
    # Show summary
    if results['total_processed'] > 0:
        st.success(f"📊 Processing complete: {len(results['successful'])} invoices created, {len(results['failed'])} failed")
        
        # Refresh the page to show new data
        st.rerun()

def render_invoice_card(invoice: Dict[str, Any]):
    """Render an invoice card."""
    with st.container():
        # Header
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{invoice.get('supplier', 'Unknown Supplier')}**")
            st.caption(f"Invoice #{invoice.get('invoice_number', 'N/A')} • {invoice.get('date', 'Unknown Date')}")
        
        with col2:
            st.metric("Total", format_currency(invoice.get('total', 0)))
        
        with col3:
            status = invoice.get('status', 'pending')
            st.markdown(f"<span style='background-color: {get_status_badge_color(status)}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;'>{status.upper()}</span>", 
                       unsafe_allow_html=True)
        
        # Confidence badge
        confidence = invoice.get('confidence', 0)
        if confidence < 60:
            st.warning(f"⚠️ Low confidence: {format_confidence(confidence)}")
        else:
            st.info(f"📊 Confidence: {format_confidence(confidence)}")
        
        # Expandable details
        with st.expander("📋 View Details"):
            render_invoice_details(invoice)

def render_invoice_details(invoice: Dict[str, Any]):
    """Render detailed invoice information."""
    invoice_id = invoice.get('id')
    if not invoice_id:
        st.error("Invoice ID not found")
        return
    
    # Get detailed invoice data
    details = get_invoice_details(invoice_id)
    if not details:
        st.error("Failed to load invoice details")
        return
    
    # Basic info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Net Amount", format_currency(details.get('net_amount_pennies', 0)))
    with col2:
        st.metric("VAT Amount", format_currency(details.get('vat_amount_pennies', 0)))
    with col3:
        st.metric("Gross Amount", format_currency(details.get('gross_amount_pennies', 0)))
    
    # Line items
    st.subheader("📦 Line Items")
    line_items = details.get('line_items', [])
    if line_items:
        df = pd.DataFrame(line_items)
        df['Unit Price'] = df['unit_price'].apply(lambda x: format_currency(x * 100))
        df['Total'] = df['total'].apply(lambda x: format_currency(x * 100))
        df['Flagged'] = df['flagged'].apply(lambda x: '⚠️' if x else '✅')
        
        st.dataframe(
            df[['item', 'invoice_qty', 'Unit Price', 'Total', 'Flagged']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No line items found")
    
    # Issues
    issues = get_issues_for_invoice(invoice_id)
    if issues:
        st.subheader("🚨 Issues")
        for issue in issues:
            severity = issue.get('severity', 'medium')
            status = issue.get('status', 'open')
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{issue.get('issue_type', 'Unknown').replace('_', ' ').title()}**")
                st.caption(issue.get('description', ''))
            
            with col2:
                st.markdown(f"<span style='background-color: {get_severity_badge_color(severity)}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;'>{severity.upper()}</span>", 
                           unsafe_allow_html=True)
            
            with col3:
                if status == 'open':
                    if st.button(f"Resolve", key=f"resolve_{issue['id']}"):
                        resolve_issue_dialog(issue['id'])
                else:
                    st.success("✅ Resolved")
    
    # Pairing suggestions
    suggestions = get_pairing_suggestions(invoice_id)
    if suggestions:
        st.subheader("🔗 Pairing Suggestions")
        for suggestion in suggestions:
            render_pairing_suggestion(suggestion)
    
    # Debug drawer for low confidence
    confidence = details.get('confidence', 0)
    if confidence < 60:
        with st.expander("🔧 Debug Tools"):
            st.warning("Low confidence detected. You can retry OCR processing.")
            if st.button("🔄 Retry OCR", key=f"retry_{invoice_id}"):
                retry_ocr(invoice_id)

def render_pairing_suggestion(suggestion: Dict[str, Any]):
    """Render a pairing suggestion."""
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"**Delivery Note #{suggestion.get('delivery_number', 'N/A')}**")
            st.caption(f"Supplier: {suggestion.get('supplier', 'Unknown')} • Date: {suggestion.get('delivery_date', 'Unknown')}")
        
        with col2:
            similarity = suggestion.get('similarity_score', 0)
            st.metric("Similarity", f"{similarity:.1f}%")
        
        with col3:
            if st.button("✅ Confirm", key=f"confirm_{suggestion['id']}"):
                confirm_pairing(suggestion['id'])
                st.success("Pairing confirmed!")
                st.rerun()
            
            if st.button("❌ Reject", key=f"reject_{suggestion['id']}"):
                reject_pairing_dialog(suggestion['id'])

def resolve_issue_dialog(issue_id: str):
    """Show dialog to resolve an issue."""
    with st.form(f"resolve_form_{issue_id}"):
        st.write("Resolve Issue")
        resolution_notes = st.text_area("Resolution Notes", placeholder="Describe how this issue was resolved...")
        
        if st.form_submit_button("✅ Resolve"):
            if resolution_notes:
                resolve_issue(issue_id, resolution_notes)
                st.success("Issue resolved!")
                st.rerun()
            else:
                st.error("Please provide resolution notes")

def reject_pairing_dialog(pairing_id: str):
    """Show dialog to reject a pairing."""
    with st.form(f"reject_form_{pairing_id}"):
        st.write("Reject Pairing")
        rejection_reason = st.text_area("Rejection Reason", placeholder="Why is this pairing incorrect?")
        
        if st.form_submit_button("❌ Reject"):
            if rejection_reason:
                reject_pairing(pairing_id, rejection_reason)
                st.success("Pairing rejected!")
                st.rerun()
            else:
                st.error("Please provide a rejection reason")

def retry_ocr(invoice_id: str):
    """Retry OCR for an invoice."""
    with st.spinner("Retrying OCR..."):
        result = retry_ocr_for_invoice(invoice_id)
        if result['success']:
            st.success(f"OCR retry successful! New confidence: {format_confidence(result['confidence'])}")
        else:
            st.error(f"OCR retry failed: {result['error']}")
        st.rerun()

def render_invoices_list():
    """Render the invoices list."""
    st.subheader("📄 Invoices")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Status", ["All", "pending", "matched", "discrepancy", "not_paired"])
    
    with col2:
        supplier_filter = st.selectbox("Supplier", ["All"] + list(set([inv.get('supplier', 'Unknown') for inv in load_invoices_from_db()])))
    
    with col3:
        flagged_only = st.checkbox("Flagged Only")
    
    with col4:
        unmatched_only = st.checkbox("Unmatched Only")
    
    # Load and filter invoices
    invoices = load_invoices_from_db()
    
    # Apply filters
    filtered_invoices = invoices
    
    if status_filter != "All":
        filtered_invoices = [inv for inv in filtered_invoices if inv.get('status') == status_filter]
    
    if supplier_filter != "All":
        filtered_invoices = [inv for inv in filtered_invoices if inv.get('supplier') == supplier_filter]
    
    if flagged_only:
        # Get invoices with issues
        flagged_invoice_ids = set()
        for issue in get_flagged_issues():
            flagged_invoice_ids.add(issue.get('invoice_id'))
        filtered_invoices = [inv for inv in filtered_invoices if inv.get('id') in flagged_invoice_ids]
    
    if unmatched_only:
        filtered_invoices = [inv for inv in filtered_invoices if inv.get('status') == 'not_paired']
    
    # Display invoices
    if filtered_invoices:
        st.write(f"Showing {len(filtered_invoices)} invoices")
        
        for invoice in filtered_invoices:
            render_invoice_card(invoice)
            st.divider()
    else:
        st.info("No invoices found matching the selected filters")

def render_unmatched_delivery_notes():
    """Render unmatched delivery notes panel."""
    st.subheader("📦 Unmatched Delivery Notes")
    
    # This would typically load from a delivery notes table
    # For now, showing placeholder
    st.info("Delivery notes functionality will be implemented in the delivery notes module")

def render_flagged_issues_summary():
    """Render flagged issues summary."""
    st.subheader("🚨 Flagged Issues Summary")
    
    issues = get_flagged_issues()
    if issues:
        # Group by severity
        severity_counts = {}
        for issue in issues:
            severity = issue.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("High", severity_counts.get('high', 0), delta=None)
        with col2:
            st.metric("Medium", severity_counts.get('medium', 0), delta=None)
        with col3:
            st.metric("Low", severity_counts.get('low', 0), delta=None)
        
        # Show recent issues
        st.write("**Recent Issues:**")
        for issue in issues[:5]:  # Show last 5
            severity = issue.get('severity', 'medium')
            st.write(f"• {issue.get('description', 'No description')} ({severity})")
    else:
        st.success("✅ No flagged issues")

def main():
    """Main invoices page."""
    st.set_page_config(
        page_title="Invoices - Owlin",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Invoices Management")
    
    # Check license status
    license_status = check_license_status()
    if license_status == 'limited':
        st.warning("⚠️ Limited Mode: Some features are restricted. Please upgrade your license for full functionality.")
    
    # Split layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Left column: Invoices list with upload panel
        render_upload_panel()
        st.divider()
        render_invoices_list()
    
    with col2:
        # Right column: Unmatched delivery notes and flagged issues
        render_unmatched_delivery_notes()
        st.divider()
        render_flagged_issues_summary()
    
    # Footer
    st.divider()
    st.caption("Owlin Invoice Management System - Enhanced with full OCR pipeline and issue detection")

if __name__ == "__main__":
    main()
