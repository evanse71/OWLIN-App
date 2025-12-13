"""
UI Components for Owlin App
Reusable components for invoice cards, pairing suggestions, and other UI elements.
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

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
        'pending': '#ff9500',
        'matched': '#34c759',
        'discrepancy': '#ff3b30',
        'not_paired': '#007aff',
        'completed': '#34c759',
        'failed': '#ff3b30'
    }
    return colors.get(status, '#8e8e93')

def get_severity_badge_color(severity: str) -> str:
    """Get badge color for issue severity."""
    colors = {
        'low': '#34c759',
        'medium': '#ff9500',
        'high': '#ff3b30'
    }
    return colors.get(severity, '#8e8e93')

def render_status_badge(status: str) -> str:
    """Render a status badge."""
    color = get_status_badge_color(status)
    return f"""
    <span style="
        background-color: {color}; 
        color: white; 
        padding: 4px 12px; 
        border-radius: 12px; 
        font-size: 12px; 
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    ">{status}</span>
    """

def render_severity_badge(severity: str) -> str:
    """Render a severity badge."""
    color = get_severity_badge_color(severity)
    return f"""
    <span style="
        background-color: {color}; 
        color: white; 
        padding: 2px 8px; 
        border-radius: 8px; 
        font-size: 10px; 
        font-weight: 600;
        text-transform: uppercase;
    ">{severity}</span>
    """

def render_confidence_badge(confidence: float) -> str:
    """Render a confidence badge."""
    if confidence is None:
        color = "#8e8e93"
        text = "Unknown"
    elif confidence >= 80:
        color = "#34c759"
        text = f"{confidence:.1f}%"
    elif confidence >= 60:
        color = "#ff9500"
        text = f"{confidence:.1f}%"
    else:
        color = "#ff3b30"
        text = f"{confidence:.1f}%"
    
    return f"""
    <span style="
        background-color: {color}; 
        color: white; 
        padding: 2px 8px; 
        border-radius: 8px; 
        font-size: 10px; 
        font-weight: 600;
    ">{text}</span>
    """

class InvoiceCard:
    """Invoice card component with full functionality."""
    
    def __init__(self, invoice: Dict[str, Any]):
        self.invoice = invoice
        self.invoice_id = invoice.get('id')
    
    def render(self):
        """Render the complete invoice card."""
        with st.container():
            # Main card container with border
            st.markdown("""
                <div style="
                    border: 1px solid #e1e5e9;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                    background-color: #ffffff;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
            """, unsafe_allow_html=True)
            
            # Header section
            self._render_header()
            
            # Status and confidence section
            self._render_status_section()
            
            # Expandable details
            with st.expander("📋 View Details", expanded=False):
                self._render_details()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _render_header(self):
        """Render the card header."""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            supplier = self.invoice.get('supplier', 'Unknown Supplier')
            invoice_number = self.invoice.get('invoice_number', 'N/A')
            date = self.invoice.get('date', 'Unknown Date')
            
            st.markdown(f"""
                <div style="margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #1d1d1f; font-size: 16px; font-weight: 600;">
                        {supplier}
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #86868b; font-size: 14px;">
                        Invoice #{invoice_number} • {date}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total = self.invoice.get('total', 0)
            st.metric("Total", format_currency(total))
        
        with col3:
            status = self.invoice.get('status', 'pending')
            st.markdown(render_status_badge(status), unsafe_allow_html=True)
    
    def _render_status_section(self):
        """Render status and confidence information."""
        confidence = self.invoice.get('confidence', 0)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(render_confidence_badge(confidence), unsafe_allow_html=True)
        
        with col2:
            if confidence < 60:
                st.warning("⚠️ Low confidence - review recommended")
            elif confidence < 80:
                st.info("📊 Medium confidence")
            else:
                st.success("✅ High confidence")
    
    def _render_details(self):
        """Render detailed invoice information."""
        if not self.invoice_id:
            st.error("Invoice ID not found")
            return
        
        # Import here to avoid circular imports
        from app.database import get_invoice_details, get_issues_for_invoice, get_pairing_suggestions
        
        # Get detailed invoice data
        details = get_invoice_details(self.invoice_id)
        if not details:
            st.error("Failed to load invoice details")
            return
        
        # Basic info metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Net Amount", format_currency(details.get('net_amount_pennies', 0)))
        with col2:
            st.metric("VAT Amount", format_currency(details.get('vat_amount_pennies', 0)))
        with col3:
            st.metric("Gross Amount", format_currency(details.get('gross_amount_pennies', 0)))
        
        # Line items table
        self._render_line_items(details)
        
        # Issues section
        self._render_issues()
        
        # Pairing suggestions
        self._render_pairing_suggestions()
        
        # Debug tools for low confidence
        self._render_debug_tools(details)
    
    def _render_line_items(self, details: Dict[str, Any]):
        """Render line items table."""
        st.subheader("📦 Line Items")
        line_items = details.get('line_items', [])
        
        if line_items:
            # Prepare data for display
            display_data = []
            for item in line_items:
                display_data.append({
                    'Item': item.get('item', ''),
                    'Qty': item.get('qty', 0),
                    'Unit Price': format_currency(item.get('unit_price', 0) * 100),
                    'Total': format_currency(item.get('total', 0) * 100),
                    'Status': '⚠️ Flagged' if item.get('flagged') else '✅ OK'
                })
            
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No line items found")
    
    def _render_issues(self):
        """Render issues section."""
        from app.database import get_issues_for_invoice
        
        issues = get_issues_for_invoice(self.invoice_id)
        if issues:
            st.subheader("🚨 Issues")
            
            for issue in issues:
                self._render_issue_item(issue)
        else:
            st.success("✅ No issues detected")
    
    def _render_issue_item(self, issue: Dict[str, Any]):
        """Render a single issue item."""
        severity = issue.get('severity', 'medium')
        status = issue.get('status', 'open')
        issue_type = issue.get('issue_type', 'Unknown').replace('_', ' ').title()
        description = issue.get('description', '')
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{issue_type}**")
                st.caption(description)
            
            with col2:
                st.markdown(render_severity_badge(severity), unsafe_allow_html=True)
            
            with col3:
                if status == 'open':
                    if st.button("Resolve", key=f"resolve_{issue['id']}", type="secondary"):
                        self._show_resolve_dialog(issue['id'])
                else:
                    st.success("✅ Resolved")
    
    def _render_pairing_suggestions(self):
        """Render pairing suggestions."""
        from app.database import get_pairing_suggestions
        
        suggestions = get_pairing_suggestions(self.invoice_id)
        if suggestions:
            st.subheader("🔗 Pairing Suggestions")
            
            for suggestion in suggestions:
                self._render_pairing_suggestion(suggestion)
        else:
            st.info("No pairing suggestions available")
    
    def _render_pairing_suggestion(self, suggestion: Dict[str, Any]):
        """Render a single pairing suggestion."""
        delivery_number = suggestion.get('delivery_number', 'N/A')
        supplier = suggestion.get('supplier', 'Unknown')
        delivery_date = suggestion.get('delivery_date', 'Unknown')
        similarity = suggestion.get('similarity_score', 0)
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**Delivery Note #{delivery_number}**")
                st.caption(f"Supplier: {supplier} • Date: {delivery_date}")
            
            with col2:
                st.metric("Similarity", f"{similarity:.1f}%")
            
            with col3:
                if st.button("✅ Confirm", key=f"confirm_{suggestion['id']}", type="primary"):
                    self._confirm_pairing(suggestion['id'])
                
                if st.button("❌ Reject", key=f"reject_{suggestion['id']}", type="secondary"):
                    self._show_reject_dialog(suggestion['id'])
    
    def _render_debug_tools(self, details: Dict[str, Any]):
        """Render debug tools for low confidence invoices."""
        confidence = details.get('confidence', 0)
        
        if confidence < 60:
            with st.expander("🔧 Debug Tools"):
                st.warning("Low confidence detected. You can retry OCR processing.")
                
                if st.button("🔄 Retry OCR", key=f"retry_{self.invoice_id}", type="secondary"):
                    self._retry_ocr()
    
    def _show_resolve_dialog(self, issue_id: str):
        """Show dialog to resolve an issue."""
        with st.form(f"resolve_form_{issue_id}"):
            st.write("Resolve Issue")
            resolution_notes = st.text_area(
                "Resolution Notes", 
                placeholder="Describe how this issue was resolved...",
                key=f"resolution_{issue_id}"
            )
            
            if st.form_submit_button("✅ Resolve"):
                if resolution_notes:
                    from app.database import resolve_issue
                    resolve_issue(issue_id, resolution_notes)
                    st.success("Issue resolved!")
                    st.rerun()
                else:
                    st.error("Please provide resolution notes")
    
    def _show_reject_dialog(self, pairing_id: str):
        """Show dialog to reject a pairing."""
        with st.form(f"reject_form_{pairing_id}"):
            st.write("Reject Pairing")
            rejection_reason = st.text_area(
                "Rejection Reason", 
                placeholder="Why is this pairing incorrect?",
                key=f"rejection_{pairing_id}"
            )
            
            if st.form_submit_button("❌ Reject"):
                if rejection_reason:
                    from app.database import reject_pairing
                    reject_pairing(pairing_id, rejection_reason)
                    st.success("Pairing rejected!")
                    st.rerun()
                else:
                    st.error("Please provide a rejection reason")
    
    def _confirm_pairing(self, pairing_id: str):
        """Confirm a pairing."""
        from app.database import confirm_pairing
        confirm_pairing(pairing_id)
        st.success("Pairing confirmed!")
        st.rerun()
    
    def _retry_ocr(self):
        """Retry OCR for the invoice."""
        from app.enhanced_file_processor import retry_ocr_for_invoice
        
        with st.spinner("Retrying OCR..."):
            result = retry_ocr_for_invoice(self.invoice_id)
            if result['success']:
                st.success(f"OCR retry successful! New confidence: {format_confidence(result['confidence'])}")
            else:
                st.error(f"OCR retry failed: {result['error']}")
            st.rerun()

class DocumentPairingSuggestionCard:
    """Document pairing suggestion card component."""
    
    def __init__(self, suggestion: Dict[str, Any]):
        self.suggestion = suggestion
        self.pairing_id = suggestion.get('id')
    
    def render(self):
        """Render the pairing suggestion card."""
        with st.container():
            # Card container
            st.markdown("""
                <div style="
                    border: 1px solid #e1e5e9;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    background-color: #f8f9fa;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                ">
            """, unsafe_allow_html=True)
            
            # Header
            self._render_header()
            
            # Similarity score
            self._render_similarity()
            
            # Action buttons
            self._render_actions()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _render_header(self):
        """Render the card header."""
        delivery_number = self.suggestion.get('delivery_number', 'N/A')
        supplier = self.suggestion.get('supplier', 'Unknown')
        delivery_date = self.suggestion.get('delivery_date', 'Unknown')
        
        st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <h4 style="margin: 0; color: #1d1d1f; font-size: 14px; font-weight: 600;">
                    Delivery Note #{delivery_number}
                </h4>
                <p style="margin: 4px 0 0 0; color: #86868b; font-size: 12px;">
                    {supplier} • {delivery_date}
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    def _render_similarity(self):
        """Render similarity score."""
        similarity = self.suggestion.get('similarity_score', 0)
        
        # Color based on similarity score
        if similarity >= 80:
            color = "#34c759"
        elif similarity >= 60:
            color = "#ff9500"
        else:
            color = "#ff3b30"
        
        st.markdown(f"""
            <div style="text-align: center; margin: 8px 0;">
                <span style="
                    background-color: {color}; 
                    color: white; 
                    padding: 4px 12px; 
                    border-radius: 12px; 
                    font-size: 12px; 
                    font-weight: 600;
                ">{similarity:.1f}% Match</span>
            </div>
        """, unsafe_allow_html=True)
    
    def _render_actions(self):
        """Render action buttons."""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirm", key=f"confirm_pair_{self.pairing_id}", type="primary"):
                self._confirm_pairing()
        
        with col2:
            if st.button("❌ Reject", key=f"reject_pair_{self.pairing_id}", type="secondary"):
                self._show_reject_dialog()
    
    def _confirm_pairing(self):
        """Confirm the pairing."""
        from app.database import confirm_pairing
        confirm_pairing(self.pairing_id)
        st.success("Pairing confirmed!")
        st.rerun()
    
    def _show_reject_dialog(self):
        """Show dialog to reject the pairing."""
        with st.form(f"reject_pairing_form_{self.pairing_id}"):
            st.write("Reject Pairing")
            rejection_reason = st.text_area(
                "Rejection Reason", 
                placeholder="Why is this pairing incorrect?",
                key=f"rejection_reason_{self.pairing_id}"
            )
            
            if st.form_submit_button("❌ Reject"):
                if rejection_reason:
                    from app.database import reject_pairing
                    reject_pairing(self.pairing_id, rejection_reason)
                    st.success("Pairing rejected!")
                    st.rerun()
                else:
                    st.error("Please provide a rejection reason")

def render_upload_progress(file_name: str, progress: float):
    """Render upload progress indicator."""
    st.progress(progress)
    st.caption(f"Processing {file_name}...")

def render_processing_status(status: str, message: str = ""):
    """Render processing status indicator."""
    status_colors = {
        'pending': '#ff9500',
        'processing': '#007aff',
        'completed': '#34c759',
        'failed': '#ff3b30'
    }
    
    color = status_colors.get(status, '#8e8e93')
    
    st.markdown(f"""
        <div style="
            background-color: {color}; 
            color: white; 
            padding: 8px 16px; 
            border-radius: 8px; 
            font-size: 14px; 
            font-weight: 600;
            margin: 8px 0;
        ">{status.upper()}{f' - {message}' if message else ''}</div>
    """, unsafe_allow_html=True)
