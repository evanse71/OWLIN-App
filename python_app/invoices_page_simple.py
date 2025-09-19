# -*- coding: utf-8 -*-
"""
Invoices Page Module for OWLIN App
Handles invoice processing, matching, and submission functionality.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import time
from typing import List, Dict, Optional, Tuple, Any
import requests
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
MAX_FILE_SIZE_MB = 10
SUPPORTED_FORMATS = {
    'invoice': ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'],
    'delivery_note': ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
}

# --- Database Functions ---
def load_invoices_from_db():
    """Load invoices from database."""
    try:
        # This would connect to your actual database
        # For now, return empty list
        return []
    except Exception as e:
        logger.error(f"Error loading invoices: {e}")
        return []

def get_processing_status_summary():
    """Get processing status summary from backend."""
    try:
        # This would call your actual backend API
        return {
            "invoices": {
                "total_value": 0,
                "discrepancy": 0,
                "total_error": 0,
                "total_count": 0,
                "paired_count": 0,
                "processing_count": 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting status summary: {e}")
        return None

# --- Utility Functions ---
def get_enhanced_status_icon(status):
    """Get enhanced status icon HTML with better accessibility and visual feedback."""
    icons = {
        "matched": "✅",
        "discrepancy": "⚠️", 
        "not_paired": "❌",
        "pending": "⏳",
        "processing": "🔄"
    }
    return icons.get(status, icons["pending"])

def get_status_color(status):
    """Get color for status text."""
    colors = {
        "matched": "#4CAF50",
        "discrepancy": "#f1c232", 
        "not_paired": "#ff3b30",
        "pending": "#888",
        "processing": "#007bff"
    }
    return colors.get(status, "#888")

def get_status_counts(invoices):
    """Get counts of each status type."""
    counts = {
        "matched": 0,
        "discrepancy": 0,
        "not_paired": 0,
        "pending": 0,
        "processing": 0
    }
    for inv in invoices:
        status = inv.get('status', 'pending')
        if status in counts:
            counts[status] += 1
    return counts

def detect_status_changes(previous_invoices, current_invoices):
    """Detect status changes between previous and current invoice lists."""
    changes = []
    if not previous_invoices:
        return changes
    prev_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in previous_invoices}
    curr_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in current_invoices}
    for inv_id, current_status in curr_lookup.items():
        if inv_id in prev_lookup:
            previous_status = prev_lookup[inv_id]
            if previous_status != current_status:
                invoice_number = next((inv.get('invoice_number', 'Unknown') for inv in current_invoices if inv.get('id') == inv_id), 'Unknown')
                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")
    return changes

def get_status_icon(status):
    """Get the appropriate status icon HTML for an invoice status."""
    icons = {
        "matched": '<span class="owlin-invoice-status-icon owlin-invoice-status-matched" aria-label="Matched">✔️</span>',
        "discrepancy": '<span class="owlin-invoice-status-icon owlin-invoice-status-discrepancy" aria-label="Discrepancy">⚠️</span>',
        "not_paired": '<span class="owlin-invoice-status-icon owlin-invoice-status-not_paired" aria-label="Not Paired">❌</span>',
        "pending": '<span class="owlin-invoice-status-icon owlin-invoice-status-pending" aria-label="Pending">⏳</span>',
        "processing": '<span class="owlin-invoice-status-icon owlin-invoice-status-processing" aria-label="Processing">🔄</span>'
    }
    return icons.get(status, icons["pending"])

def render_metric_box(label, value, highlight=False):
    """Render a metric box with optional highlighting and enhanced styling."""
    highlight_class = " highlighted" if highlight else ""
    return f'<div class="owlin-metric-box{highlight_class}" role="region" aria-label="{label}: {value}">{label}<br>{value}</div>'

def sanitize_text(text):
    """Sanitize text for safe display and prevent XSS attacks."""
    if not text:
        return ''
    
    try:
        import html
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', str(text))
        
        # HTML encode special characters
        text = html.escape(text)
        
        # Limit length to prevent overflow
        if len(text) > 1000:
            text = text[:997] + '...'
        
        return text
    except Exception:
        return str(text)[:1000] if str(text) else ''

def format_currency(amount):
    """Format currency consistently with proper locale and error handling."""
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

# --- Component: Summary Metrics ---
def render_summary_metrics(metrics_data=None):
    """Render the summary metrics row showing total value, issues count, and error amount with sticky header."""
    try:
        # Fetch metrics data if not provided
        if metrics_data is None:
            summary = get_processing_status_summary()
            if summary and "invoices" in summary:
                metrics_data = {
                    'total_value': summary["invoices"].get("total_value", 0),
                    'num_issues': summary["invoices"].get("discrepancy", 0),
                    'total_error': summary["invoices"].get("total_error", 0),
                    'total_invoices': summary["invoices"].get("total_count", 0),
                    'paired_invoices': summary["invoices"].get("paired_count", 0),
                    'processing_invoices': summary["invoices"].get("processing_count", 0)
                }
            else:
                metrics_data = {
                    'total_value': 0,
                    'num_issues': 0,
                    'total_error': 0,
                    'total_invoices': 0,
                    'paired_invoices': 0,
                    'processing_invoices': 0
                }
        
        # Ensure metrics_data has all required fields
        total_value = metrics_data.get('total_value', 0)
        num_issues = metrics_data.get('num_issues', 0)
        total_error = metrics_data.get('total_error', 0)
        total_invoices = metrics_data.get('total_invoices', 0)
        paired_invoices = metrics_data.get('paired_invoices', 0)
        processing_invoices = metrics_data.get('processing_invoices', 0)
        
        # Render metrics with enhanced styling
        st.markdown("### Summary Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Value", format_currency(total_value))
            st.metric("Total Invoices", total_invoices)
        
        with col2:
            st.metric("Paired Invoices", paired_invoices)
            st.metric("Processing", processing_invoices)
        
        with col3:
            st.metric("Issues Detected", num_issues)
            st.metric("Total Error", format_currency(total_error))
        
    except Exception as e:
        logger.error(f"Error rendering summary metrics: {e}")
        st.error("Unable to load summary metrics")

# --- Component: Invoice List ---
def render_invoice_list(invoices, selected_index=None, on_select=None):
    """Render the invoice list with enhanced functionality."""
    try:
        # Initialize session state for status checking
        if 'last_status_check' not in st.session_state:
            st.session_state.last_status_check = datetime.now()
        
        # Check if we need to refresh statuses
        time_since_last_check = (datetime.now() - st.session_state.last_status_check).total_seconds()
        if time_since_last_check > 30:  # Refresh every 30 seconds
            try:
                # Reload invoices with fresh statuses
                fresh_invoices = load_invoices_from_db()
                if fresh_invoices:
                    invoices = fresh_invoices
                    st.session_state.last_status_check = datetime.now()
                    
                    # Announce status updates to screen readers
                    status_changes = detect_status_changes(st.session_state.get('previous_invoices', []), invoices)
                    if status_changes:
                        for change in status_changes:
                            announce_to_screen_reader(f"Status update: {change}", 'polite')
                
                # Store current state for next comparison
                st.session_state.previous_invoices = invoices.copy()
                
            except Exception as e:
                st.warning(f"⚠️ Unable to refresh statuses: {str(e)}")
        
        # Handle selection state with enhanced logic
        if selected_index is None:
            # Use session state if no external selection provided
            if 'selected_invoice_idx' not in st.session_state:
                st.session_state.selected_invoice_idx = 0
            selected_index = st.session_state.selected_invoice_idx
        
        # Ensure selected index is valid
        if selected_index >= len(invoices):
            selected_index = 0 if invoices else None
        
        if invoices:
            # Enhanced header with real-time status summary
            status_counts = get_status_counts(invoices)
            total_value = sum(inv.get('total', 0) for inv in invoices)
            
            st.markdown(f"**📄 {len(invoices)} invoice{'s' if len(invoices) != 1 else ''} • 💰 {format_currency(total_value)}**")
            
            # Status summary
            status_text = []
            if status_counts["matched"] > 0:
                status_text.append(f"✅ {status_counts['matched']} matched")
            if status_counts["discrepancy"] > 0:
                status_text.append(f"⚠️ {status_counts['discrepancy']} discrepancies")
            if status_counts["not_paired"] > 0:
                status_text.append(f"❌ {status_counts['not_paired']} not paired")
            if status_counts["processing"] > 0:
                status_text.append(f"🔄 {status_counts['processing']} processing")
            if status_counts["pending"] > 0:
                status_text.append(f"⏳ {status_counts['pending']} pending")
            
            if status_text:
                st.markdown(f"*{', '.join(status_text)}*")
            
            st.markdown(f"*🔄 Auto-refreshing every 30 seconds • Last updated: {datetime.now().strftime('%H:%M:%S')}*")
            
            # Enhanced invoice cards with real-time statuses
            for idx, inv in enumerate(invoices):
                # Get enhanced status information
                status = inv.get('status', 'pending')
                status_icon = get_enhanced_status_icon(status)
                is_selected = (idx == selected_index)
                
                # Create unique key for each invoice card
                card_key = f"invoice_card_{inv.get('id', idx)}_{idx}"
                
                # Enhanced invoice data extraction
                invoice_number = sanitize_text(inv.get('invoice_number', 'N/A'))
                supplier = sanitize_text(inv.get('supplier', 'N/A'))
                date = sanitize_text(inv.get('date', ''))
                total = format_currency(inv.get('total', 0))
                
                # Enhanced clickable invoice card with keyboard support
                if st.button(
                    f"{status_icon} {invoice_number} from {supplier} - {total}", 
                    key=card_key, 
                    help=f"Select invoice {invoice_number} from {supplier} (Status: {status})",
                    use_container_width=True
                ):
                    # Handle selection with enhanced feedback
                    if on_select:
                        # Use external callback if provided
                        on_select(idx, inv)
                    else:
                        # Update session state
                        st.session_state.selected_invoice_idx = idx
                        announce_to_screen_reader(f"Selected invoice {invoice_number} from {supplier}")
                        st.rerun()
                
                # Show additional details for selected invoice
                if is_selected:
                    st.markdown(f"**Selected:** {invoice_number} • {supplier} • {date} • {total}")
                    st.markdown(f"**Status:** {status.replace('_', ' ').title()}")
        else:
            # Enhanced empty state
            st.markdown("### 📄 No Invoices Found")
            st.markdown("Upload invoice files to get started with processing.")
            st.markdown("*Supported formats: PDF, JPG, PNG, TIFF*")
            
    except Exception as e:
        logger.error(f"Error rendering invoice list: {e}")
        st.error("Unable to load invoice list")

# --- Component: Upload Box ---
def render_upload_box(label, key, accepted_formats, file_type, max_size_mb=10):
    """Render an enhanced upload box with accessibility features."""
    try:
        st.markdown(f"### {label}")
        st.markdown(f"Supported formats: {', '.join(accepted_formats)} • Max size: {max_size_mb}MB")
        
        uploaded_file = st.file_uploader(
            label,
            type=[ext.replace('.', '') for ext in accepted_formats],
            key=key,
            help=f"Upload {file_type} files. Supported formats: {', '.join(accepted_formats)}",
            accept_multiple_files=True
        )
        
        return uploaded_file
        
    except Exception as e:
        logger.error(f"Error rendering upload box: {e}")
        return None

# --- Component: Footer Buttons ---
def render_footer_buttons(on_clear=None, on_submit=None, disabled=False, show_loading=False):
    """Render footer buttons with enhanced functionality."""
    try:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🗑️ Clear All", help="Clear all uploaded files and data", disabled=disabled):
                if on_clear:
                    on_clear()
                else:
                    # Default clear behavior
                    for key in list(st.session_state.keys()):
                        if isinstance(key, str) and key.startswith('uploaded_'):
                            del st.session_state[key]
                    st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", help="Refresh the current page", disabled=disabled):
                st.rerun()
        
        with col3:
            submit_disabled = disabled or show_loading
            submit_text = "⏳ Processing..." if show_loading else "📤 Submit to OWLIN"
            
            if st.button(submit_text, help="Submit processed data to OWLIN", disabled=submit_disabled):
                if on_submit:
                    on_submit()
                else:
                    st.info("Submit functionality not implemented")
        
    except Exception as e:
        logger.error(f"Error rendering footer buttons: {e}")
        st.error("Unable to render footer buttons")

# --- Accessibility Functions ---
def announce_to_screen_reader(message, priority='polite'):
    """Announce message to screen readers."""
    try:
        st.markdown(f"""
            <div aria-live="{priority}" aria-atomic="true" style="position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;">
                {message}
            </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error announcing to screen reader: {e}")

def add_accessibility_enhancements():
    """Add accessibility enhancements to the page."""
    try:
        st.markdown("""
            <style>
            /* Accessibility enhancements */
            .owlin-invoice-card:focus {
                outline: 2px solid #007bff;
                outline-offset: 2px;
            }
            
            .owlin-invoice-card[aria-selected="true"] {
                border: 2.5px solid #222222 !important;
            }
            
            /* High contrast mode support */
            @media (prefers-contrast: high) {
                .owlin-invoice-card {
                    border: 2px solid #000;
                }
            }
            
            /* Reduced motion support */
            @media (prefers-reduced-motion: reduce) {
                .owlin-invoice-card {
                    transition: none;
                }
            }
            </style>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Error adding accessibility enhancements: {e}")

def inject_invoice_page_grid_styles():
    st.markdown("""
    <style>
    body, .stApp {
        background: #f5f6fa !important;
    }
    .owlin-grid-container {
        width: 1200px;
        min-width: 1200px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        grid-auto-rows: min-content;
        gap: 24px;
        padding-left: 32px;
        padding-right: 32px;
        box-sizing: border-box;
    }
    .owlin-section {
        grid-column: 1 / span 12;
        margin-bottom: 40px;
    }
    /* Upload Card Drag & Drop */
    .owlin-section.dragover > div[role="region"] {
        border: 2.5px solid #4F8CFF !important;
        background: #f0f6ff !important;
        transition: border-color 0.2s, background 0.2s;
    }
    /* Responsive: 900px-1200px */
    @media (max-width: 1200px) {
        .owlin-grid-container {
            width: 100vw;
            min-width: 0;
            padding-left: 16px;
            padding-right: 16px;
        }
        .owlin-section {
            margin-bottom: 32px;
        }
        .owlin-section[style*='grid-column: 2 / span 10;'] {
            grid-column: 1 / span 12 !important;
        }
    }
    /* Responsive: <900px */
    @media (max-width: 900px) {
        .owlin-grid-container {
            width: 100vw;
            min-width: 0;
            padding-left: 8px;
            padding-right: 8px;
        }
        .owlin-section {
            margin-bottom: 24px;
        }
        .owlin-section[style*='grid-column: 2 / span 10;'] {
            grid-column: 1 / span 12 !important;
        }
        .owlin-section > div[role="region"] {
            flex-direction: column !important;
            height: auto !important;
            padding: 16px !important;
        }
        .owlin-upload-zone {
            margin: 0 0 16px 0 !important;
            width: 100% !important;
            min-width: 0 !important;
        }
        .owlin-metric-box {
            font-size: 1rem !important;
            padding: 0.7rem 0.5rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_upload_and_metrics_section():
    # --- Upload Documents Card ---
    st.markdown('''
    <div class="owlin-section" style="grid-column: 2 / span 10;">
      <div role="region" aria-label="Upload invoices and delivery notes"
           style="height:220px; background:#fff; border-radius:24px; box-shadow:0 4px 24px rgba(0,0,0,0.06); padding:32px; display:flex; flex-direction:row; gap:32px; align-items:center; justify-content:center;">
        <!-- Upload Zone 1 -->
        <div tabindex="0" aria-label="Upload Invoices" class="owlin-upload-zone" style="flex:1; height:160px; border:2px dashed #e0e4ea; border-radius:20px; background:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; margin-right:16px; transition: border-color 0.2s, background 0.2s;">
          <svg width="48" height="48" fill="none" stroke="#4F8CFF" stroke-width="2" viewBox="0 0 24 24" style="margin-bottom:8px;"><path d="M12 19V6M5 12l7-7 7 7"/></svg>
          <div style="font-weight:700; font-size:1.1rem; margin-bottom:4px;">+ Upload Invoices</div>
          <div style="font-size:0.95rem; color:#888;">PDF, PNG, JPG, JPEG, ZIP • Max 10MB</div>
          <div style="margin-top:8px; width:100%;">
            <div style="display:flex; justify-content:center;">
              <div style="width:90%;">
    ''', unsafe_allow_html=True)
    invoice_files = st.file_uploader(
        "Upload Invoices",
        type=["pdf", "png", "jpg", "jpeg", "zip"],
        key="upload_invoices",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    st.markdown('''
              </div>
            </div>
          </div>
        </div>
        <!-- Upload Zone 2 -->
        <div tabindex="0" aria-label="Upload Delivery Notes" class="owlin-upload-zone" style="flex:1; height:160px; border:2px dashed #e0e4ea; border-radius:20px; background:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; margin-left:16px; transition: border-color 0.2s, background 0.2s;">
          <svg width="48" height="48" fill="none" stroke="#4F8CFF" stroke-width="2" viewBox="0 0 24 24" style="margin-bottom:8px;"><path d="M12 19V6M5 12l7-7 7 7"/></svg>
          <div style="font-weight:700; font-size:1.1rem; margin-bottom:4px;">+ Upload Delivery Notes</div>
          <div style="font-size:0.95rem; color:#888;">PDF, PNG, JPG, JPEG, ZIP • Max 10MB</div>
          <div style="margin-top:8px; width:100%;">
            <div style="display:flex; justify-content:center;">
              <div style="width:90%;">
    ''', unsafe_allow_html=True)
    delivery_files = st.file_uploader(
        "Upload Delivery Notes",
        type=["pdf", "png", "jpg", "jpeg", "zip"],
        key="upload_delivery_notes",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    st.markdown('''
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    ''', unsafe_allow_html=True)

    # --- Summary Metrics Card ---
    metrics = [
        ("Total Invoice Value", "£5,503.04"),
        ("Number of Issues", "4"),
        ("Total Error Value", "£89.48"),
        ("Processed Files", "12"),
        ("Matched Invoices", "8"),
        ("Pending Files", "2"),
    ]
    st.markdown('''
    <div class="owlin-section" style="grid-column: 2 / span 10;">
      <div style="height:140px; background:#fff; border-radius:24px; box-shadow:0 4px 24px rgba(0,0,0,0.06); padding:24px 32px; display:grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(2, 1fr); gap:24px;">
    ''', unsafe_allow_html=True)
    for i, (label, value) in enumerate(metrics):
        st.markdown(f'''
        <div style="background:#22223B; color:#fff; border-radius:16px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-family:Inter,sans-serif; font-size:1.15rem; font-weight:600; padding:1.2rem 1rem;">
            <div style="font-size:1.25rem; font-weight:700; margin-bottom:0.2rem;">{value}</div>
            <div style="font-size:1rem; font-weight:500;">{label}</div>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('''
      </div>
    </div>
    ''', unsafe_allow_html=True)

# --- Main Page Function ---
def render_invoices_page():
    """Main function to render the invoices page."""
    try:
        # Add accessibility enhancements
        add_accessibility_enhancements()
        
        # Page header
        st.title("📄 Invoice Processing")
        st.markdown("Upload and process invoice files with delivery notes")
        
        # Initialize session state
        if 'invoices' not in st.session_state:
            st.session_state.invoices = []
        
        # Load invoices
        invoices = load_invoices_from_db()
        if invoices:
            st.session_state.invoices = invoices
        
        inject_invoice_page_grid_styles()
        st.markdown('<div class="owlin-grid-container">', unsafe_allow_html=True)
        # --- Upload Section ---
        render_upload_and_metrics_section()
        st.markdown('</div>', unsafe_allow_html=True)
        # --- Invoice List ---
        st.markdown('<div class="owlin-section">', unsafe_allow_html=True)
        st.markdown("### 📋 Invoice List")
        render_invoice_list(
            st.session_state.invoices,
            selected_index=st.session_state.get('selected_invoice_idx', 0)
        )
        st.markdown('</div>', unsafe_allow_html=True)
        # --- Issues Detected ---
        st.markdown('<div class="owlin-section">', unsafe_allow_html=True)
        st.markdown("### 📊 Issues Detected")
        st.markdown("<!-- Issues Detected UI goes here -->")
        st.markdown('</div>', unsafe_allow_html=True)
        # --- Footer Buttons ---
        st.markdown('<div class="owlin-section" style="display:flex;justify-content:flex-end;align-items:center;">', unsafe_allow_html=True)
        st.markdown("---")
        render_footer_buttons(
            on_clear=lambda: st.rerun(),
            on_submit=lambda: st.success("Data submitted successfully!")
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Error rendering invoices page: {e}")
        st.error("An error occurred while loading the invoices page")

# --- Error Boundary ---
def add_error_boundary(func):
    """Add error boundary to functions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            st.error(f"An error occurred: {str(e)}")
            return None
    return wrapper

# --- Main Execution ---
if __name__ == "__main__":
    render_invoices_page()
