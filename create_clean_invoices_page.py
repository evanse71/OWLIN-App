#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def create_clean_invoices_page():
    """Create a completely clean version of invoices_page.py."""
    
    clean_content = '''# -*- coding: utf-8 -*-
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
        st.markdown(f'''
            <div class="owlin-summary-metrics" style="position: sticky; top: 0; z-index: 100; background: white; padding: 1rem; border-bottom: 1px solid #eee; margin-bottom: 1rem;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                    {render_metric_box("Total Value", format_currency(total_value))}
                    {render_metric_box("Total Invoices", str(total_invoices))}
                    {render_metric_box("Paired Invoices", str(paired_invoices), highlight=(paired_invoices > 0))}
                    {render_metric_box("Processing", str(processing_invoices), highlight=(processing_invoices > 0))}
                    {render_metric_box("Issues Detected", str(num_issues), highlight=(num_issues > 0))}
                    {render_metric_box("Total Error", format_currency(total_error), highlight=(total_error > 0))}
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Error rendering summary metrics: {e}")
        st.error("Unable to load summary metrics")

# --- Component: Invoice List ---
def render_invoice_list(invoices, selected_index=None, expanded_index=None):
    st.markdown('<div role="list" aria-label="Invoices and delivery notes">', unsafe_allow_html=True)
    for idx, invoice in enumerate(invoices):
        is_selected = (idx == selected_index)
        is_expanded = (idx == expanded_index)
        delivery_note = invoice.get('delivery_note')
        card_status = "selected" if is_selected else ""
        aria_expanded = "true" if is_expanded else "false"
        # Card
        st.markdown(
            f'<div class="owlin-card-listitem {card_status} owlin-focusable" role="listitem" tabindex="0" aria-label="Invoice {invoice.get("invoice_number")} from {invoice.get("supplier")}, {invoice.get("date")}, status {invoice.get("status")}" aria-expanded="{aria_expanded}" '
            f'onclick="window.dispatchEvent(new CustomEvent(\'owlinCardClick\',{{detail:{idx}}}))" '
            f'onkeydown="if(event.key===\'Enter\'||event.key===\' \'){{window.dispatchEvent(new CustomEvent(\'owlinCardClick\',{{detail:{idx}}}))}}">'
            f'<div style="flex:1;">'
            f'<div style="font-weight:700;">Invoice: {invoice.get("invoice_number")}</div>'
            f'<div style="color:#666;">Supplier: {invoice.get("supplier")}</div>'
            f'<div style="color:#666;">Date: {invoice.get("date")}</div>'
            f'<div style="color:#4F8CFF;font-weight:600;">Total: £{invoice.get("total"):.2f}</div>'
            f'<div style="color:#888;">Status: {invoice.get("status").capitalize()}</div>'
            '</div>'
            # Delivery note card
            + (
                f'<div class="owlin-delivery-card {"paired" if delivery_note else "missing"}" style="margin-left:32px;flex:1;">'
                f'<div style="font-weight:700;">Delivery Note: {delivery_note.get("note_number") if delivery_note else "None"}</div>'
                f'<div style="color:#666;">Date: {delivery_note.get("date") if delivery_note else "-"}</div>'
                f'<div style="color:#4CAF50;" aria-label="Paired">' if delivery_note else '<div style="color:#FF3B30;" aria-label="Missing">'
                f'{delivery_note.get("status").capitalize() if delivery_note else "Missing"}</div>'
                f'<div style="color:#888;">Confidence: {delivery_note.get("confidence",0):.0%}</div>' if delivery_note else ''
                '</div>'
            )
            + '</div>',
            unsafe_allow_html=True
        )
        # Expansion panel
        st.markdown(
            f'<div class="owlin-expandable{" expanded" if is_expanded else ""}">'
            f'<div class="owlin-expandable-content">'
            f'<!-- Detailed content for invoice {invoice.get("invoice_number")} here -->'
            '</div></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    # JS for card click/keyboard selection
    st.components.v1.html("""
    <script>
    window.addEventListener('owlinCardClick', function(e){
        window.parent.postMessage({isStreamlitMessage: true, type: 'owlinCardClick', detail: e.detail}, '*');
    });
    </script>
    """, height=0)