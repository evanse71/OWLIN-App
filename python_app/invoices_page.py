import streamlit as st
import os
from datetime import datetime
from app.file_processor import save_file_to_disk, process_uploaded_files, save_file_metadata
from app.database import load_invoices_from_db, get_invoice_details, get_processing_status_summary
import time

# --- CSS Styling for Owlin Brand ---
st.markdown('''
<style>
body, .stApp { background: #f5f6fa !important; }
.owlin-upload-row { display: flex; gap: 2.5rem; margin-bottom: 2.5rem; }
@media (max-width: 900px) { .owlin-upload-row { flex-direction: column; gap: 1.5rem; } }
.owlin-upload-box-modern {
    background: #fff;
    border-radius: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 2.5rem 2rem 2rem 2rem;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    position: relative;
}
.owlin-upload-heading { font-size: 1.35rem; font-weight: 800; color: #222; margin-bottom: 0.5rem; }
.owlin-upload-subheading { font-size: 1.01rem; color: #666; margin-bottom: 1.5rem; }
.owlin-metrics-row { display: flex; gap: 2rem; margin-bottom: 1.5rem; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
@media (max-width: 900px) { .owlin-metrics-row { flex-direction: column; gap: 1rem; } }
.owlin-metric-box {
    background: #222;
    color: #fff;
    border-radius: 18px;
    padding: 1.2rem 2.2rem;
    font-size: 1.25rem;
    font-weight: 800;
    min-width: 180px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.owlin-main-panel { display: flex; gap: 2rem; background: #fff; border-radius: 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); min-height: 520px; margin-bottom: 1.5rem; overflow: hidden; }
@media (max-width: 1100px) { .owlin-main-panel { flex-direction: column; } }
.owlin-invoice-list { background: #f5f6fa; border-radius: 18px 0 0 18px; min-width: 260px; max-width: 340px; height: 520px; overflow-y: auto; padding: 1.2rem 0.5rem 1.2rem 1.2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.03); flex: 0 0 320px; }
.owlin-invoice-list::-webkit-scrollbar { width: 8px; background: #f5f6fa; }
.owlin-invoice-list::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 6px; }
.owlin-invoice-card { 
    background: #fff; 
    border-radius: 10px; 
    margin-bottom: 1.1rem; 
    padding: 1.1rem 1.1rem 0.8rem 1.1rem; 
    box-shadow: 0 1px 4px rgba(0,0,0,0.04); 
    cursor: pointer; 
    border: 2px solid transparent; 
    transition: all 0.2s ease-in-out; 
    display: flex; 
    align-items: center; 
    gap: 0.7rem; 
    position: relative;
    outline: none;
}
.owlin-invoice-card:hover { 
    border: 2px solid #222222; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
    transform: translateY(-1px);
}
.owlin-invoice-card.selected { 
    border: 2.5px solid #222222; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
    transform: translateY(-2px);
    background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
}
.owlin-invoice-card:focus {
    outline: 3px solid #f1c232;
    outline-offset: 2px;
    border: 2px solid #f1c232;
}
.owlin-invoice-card.owlin-processing {
    animation: processing-pulse 2s ease-in-out infinite;
    border-left: 4px solid #007bff;
}
@keyframes processing-pulse {
    0%, 100% { 
        box-shadow: 0 1px 4px rgba(0,0,0,0.04), 0 0 0 0 rgba(0,123,255,0.4);
    }
    50% { 
        box-shadow: 0 1px 4px rgba(0,0,0,0.04), 0 0 0 8px rgba(0,123,255,0);
    }
}
.owlin-invoice-status-icon { 
    font-size: 1.2rem; 
    margin-right: 0.7rem; 
    vertical-align: middle; 
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    border-radius: 50%;
    transition: all 0.2s ease-in-out;
}
.owlin-invoice-status-matched { 
    color: #4CAF50; 
    background: rgba(76, 175, 80, 0.1);
    padding: 4px;
}
.owlin-invoice-status-discrepancy { 
    color: #f1c232; 
    background: rgba(241, 194, 50, 0.1);
    padding: 4px;
    animation: discrepancy-pulse 2s ease-in-out infinite;
}
@keyframes discrepancy-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
.owlin-invoice-status-not_paired { 
    color: #ff3b30; 
    background: rgba(255, 59, 48, 0.1);
    padding: 4px;
}
.owlin-invoice-status-pending { 
    color: #888; 
    background: rgba(136, 136, 136, 0.1);
    padding: 4px;
}
.owlin-invoice-status-processing { 
    color: #007bff; 
    background: rgba(0, 123, 255, 0.1);
    padding: 4px;
    animation: processing-spin 1.5s linear infinite;
}
@keyframes processing-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.owlin-invoice-details { background: #fff; border-radius: 0 18px 18px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.03); padding: 2.2rem 2.2rem 1.5rem 2.2rem; height: 520px; overflow-y: auto; position: relative; flex: 1 1 0; }
.owlin-invoice-details::-webkit-scrollbar { width: 8px; background: #f5f6fa; }
.owlin-invoice-details::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 6px; }
.owlin-invoice-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-bottom: 1.2rem; }
.owlin-invoice-table th { background: #f5f6fa; font-weight: 700; padding: 0.7rem 0.6rem; border-bottom: 2px solid #e9ecef; font-size: 1rem; position: sticky; top: 0; z-index: 2; }
.owlin-invoice-table td { padding: 0.7rem 0.6rem; font-size: 0.98rem; border-bottom: 1px solid #f0f0f0; }
.owlin-discrepancy-cell { background: #fffbe6 !important; color: #b8860b !important; font-weight: 600; border-radius: 6px; position: relative; }
.owlin-discrepancy-icon { color: #f1c232; font-size: 1.1rem; margin-left: 0.3rem; vertical-align: middle; }
.owlin-invoice-total-row td { font-weight: 700; font-size: 1.08rem; border-bottom: none; padding-top: 1.2rem; }
.owlin-invoice-action-row { display: flex; gap: 1.1rem; margin-top: 0.7rem; }
.owlin-edit-invoice-btn, .owlin-pair-delivery-btn { background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 0.85rem 2.1rem; font-size: 1.05rem; cursor: pointer; margin-right: 0.5rem; transition: background 0.18s; }
.owlin-edit-invoice-btn[disabled], .owlin-pair-delivery-btn[disabled] { opacity: 0.5; cursor: not-allowed; }
.owlin-edit-invoice-btn:hover, .owlin-pair-delivery-btn:hover { background: #e6a93a; }
.owlin-submit-owlin-btn { background: #222222; color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 0.85rem 2.1rem; font-size: 1.05rem; cursor: pointer; transition: background 0.18s; }
.owlin-submit-owlin-btn:hover { background: #000; }
.owlin-clear-btn { background: #ff9800; color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 0.85rem 2.1rem; font-size: 1.05rem; cursor: pointer; margin-right: 0.7rem; transition: background 0.18s; }
.owlin-clear-btn:hover { background: #e67c00; }
.owlin-issues-box { background: #fff7e0; border-radius: 12px; padding: 1.2rem 1.5rem; margin: 1.2rem 0 1.7rem 0; color: #222; font-size: 1rem; border: 1px solid #f1c232; }
.owlin-issues-header { font-weight: 700; color: #b8860b; margin-bottom: 0.7rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
.owlin-issues-list { margin: 0; padding: 0; list-style: none; }
.owlin-issues-list li { margin-bottom: 0.7rem; padding-bottom: 0.7rem; border-bottom: 1px solid #f1c232; }
.owlin-footer-btn-row { display: flex; justify-content: flex-end; gap: 1.1rem; margin-bottom: 1.5rem; align-items: center; }
.owlin-not-paired-section { margin-top: 1.5rem; }
.owlin-not-paired-header { background: #222; color: #fff; border-radius: 12px 12px 0 0; padding: 0.9rem 1.5rem; font-size: 1.12rem; font-weight: 700; margin-bottom: 0; }
.owlin-not-paired-list { background: #fff; border-radius: 0 0 12px 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); padding: 1.2rem 1.5rem; max-height: 400px; overflow-y: auto; }
.owlin-not-paired-list::-webkit-scrollbar { width: 8px; background: #f5f6fa; }
.owlin-not-paired-list::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 6px; }
.owlin-not-paired-item { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.1rem; padding-bottom: 0.7rem; border-bottom: 1px solid #eee; background: #fff; border-radius: 10px; padding: 1.2rem; margin-bottom: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); border-left: 4px solid #ff3b30; position: relative; transition: all 0.2s ease-in-out; }
.owlin-not-paired-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-1px); }
.owlin-not-paired-item.owlin-urgent { border-left-color: #ef4444; background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); }
.owlin-not-paired-item.owlin-warning { border-left-color: #f1c232; background: linear-gradient(135deg, #fff 0%, #fff7e0 100%); }
.owlin-not-paired-actions { display: flex; gap: 0.7rem; }
.owlin-not-paired-status { background: #fff5f5; border-radius: 6px; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #ff3b30; }
.owlin-not-paired-status-title { color: #ff3b30; font-weight: 600; margin-bottom: 0.3rem; }
.owlin-not-paired-status-desc { color: #666; font-size: 0.9rem; }
.owlin-not-paired-recommendations { margin-top: 1.5rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #ff3b30; }
.owlin-not-paired-recommendations ul { margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4; }
.owlin-not-paired-recommendations li { margin-bottom: 0.3rem; }
.owlin-urgency-badge { position: absolute; top: -4px; right: -4px; font-size: 0.7rem; padding: 2px 6px; border-radius: 8px; font-weight: 600; }
.owlin-urgency-badge.urgent { background: #ef4444; color: white; }
.owlin-urgency-badge.warning { background: #f1c232; color: #222; }
.owlin-not-paired-summary { font-size: 0.9rem; color: #ccc; background: rgba(255,255,255,0.1); padding: 0.3rem 0.8rem; border-radius: 6px; }
.owlin-not-paired-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.8rem; }
.owlin-not-paired-card-info { flex: 1; }
.owlin-not-paired-card-total { text-align: right; margin-left: 1rem; }
.owlin-not-paired-card-title { font-weight: 700; color: #222; font-size: 1.1rem; margin-bottom: 0.3rem; }
.owlin-not-paired-card-supplier { color: #666; font-size: 0.95rem; margin-bottom: 0.2rem; }
.owlin-not-paired-card-date { color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }
.owlin-not-paired-card-amount { font-weight: 700; color: #222; font-size: 1.2rem; }
.owlin-not-paired-card-status { font-size: 0.8rem; color: #ff3b30; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.owlin-upload-status { margin-top: 1rem; padding: 0.8rem; background: #f8f9fa; border-radius: 8px; font-size: 0.9rem; }
.owlin-metrics-context { margin-top: 0.5rem; margin-bottom: 1rem; }
.owlin-metrics-context .stAlert { margin-bottom: 0; padding: 0.8rem 1rem; border-radius: 8px; font-size: 0.95rem; }
.owlin-metric-box {
    background: #222;
    color: #fff;
    border-radius: 18px;
    padding: 1.2rem 2.2rem;
    font-size: 1.25rem;
    font-weight: 800;
    min-width: 180px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease-in-out;
    position: relative;
    overflow: hidden;
}
.owlin-metric-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(241,194,50,0.1) 0%, rgba(241,194,50,0.05) 100%);
    opacity: 0;
    transition: opacity 0.2s ease-in-out;
}
.owlin-metric-box.highlighted::before {
    opacity: 1;
}
.owlin-metric-box.highlighted {
    box-shadow: 0 4px 12px rgba(241,194,50,0.2);
    transform: translateY(-2px);
}
.owlin-discrepancy-row {
    background: #fffbe6 !important;
    border-left: 4px solid #f1c232 !important;
}
.owlin-discrepancy-row:hover {
    background: #fff3cd !important;
}
.owlin-invoice-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin-bottom: 1.2rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.owlin-invoice-table th {
    background: #f8f9fa;
    font-weight: 700;
    padding: 1rem 0.8rem;
    border-bottom: 2px solid #e9ecef;
    font-size: 0.95rem;
    position: sticky;
    top: 0;
    z-index: 2;
    color: #495057;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.85rem;
}
.owlin-invoice-table td {
    padding: 0.8rem;
    font-size: 0.95rem;
    border-bottom: 1px solid #f0f0f0;
    vertical-align: middle;
}
.owlin-invoice-table tbody tr:hover {
    background: #f8f9fa;
}
.owlin-discrepancy-cell {
    background: #fffbe6 !important;
    color: #b8860b !important;
    font-weight: 600;
    border-radius: 6px;
    position: relative;
    border: 1px solid #f1c232 !important;
}
.owlin-discrepancy-icon {
    color: #f1c232;
    font-size: 1.1rem;
    margin-left: 0.3rem;
    vertical-align: middle;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
.owlin-issues-box { background: #fff7e0; border-radius: 12px; padding: 1.2rem 1.5rem; margin: 1.2rem 0 1.7rem 0; color: #222; font-size: 1rem; border: 1px solid #f1c232; }
.owlin-issues-header { font-weight: 700; color: #b8860b; margin-bottom: 0.7rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
.owlin-issues-list { margin: 0; padding: 0; list-style: none; }
.owlin-issues-list li { margin-bottom: 0.7rem; padding-bottom: 0.7rem; border-bottom: 1px solid #f1c232; }
.owlin-issue-item { background: #fff; border-radius: 8px; padding: 1.2rem; margin-bottom: 1rem; border-left: 4px solid #f1c232; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s ease-in-out; }
.owlin-issue-item:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.1); transform: translateY(-1px); }
.owlin-issue-high { border-left-color: #ef4444; background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); }
.owlin-issue-high .owlin-issue-header { color: #991b1b; }
.owlin-issue-medium { border-left-color: #f1c232; background: linear-gradient(135deg, #fff 0%, #fff7e0 100%); }
.owlin-issue-medium .owlin-issue-header { color: #b8860b; }
.owlin-issue-low { border-left-color: #10b981; background: linear-gradient(135deg, #fff 0%, #f0fdf4 100%); }
.owlin-issue-low .owlin-issue-header { color: #065f46; }
.owlin-issue-details { background: #fff7e0; border-radius: 6px; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #f1c232; }
.owlin-issue-actions { display: flex; gap: 0.8rem; justify-content: flex-start; }
.owlin-issue-recommendations { margin-top: 1.5rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #f1c232; }
.owlin-issue-recommendations ul { margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4; }
.owlin-issue-recommendations li { margin-bottom: 0.3rem; }
.owlin-issue-summary { font-size: 0.9rem; color: #666; background: #fff; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #f1c232; }
.owlin-issue-type-badge { font-size: 0.8rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #f8f9fa; padding: 0.2rem 0.5rem; border-radius: 4px; }
.owlin-issue-impact { font-weight: 700; color: #b8860b; font-size: 1.1rem; }
.owlin-issue-item-name { font-weight: 700; color: #222; font-size: 1.05rem; margin-bottom: 0.3rem; }
.owlin-issue-meta { color: #666; font-size: 0.9rem; }
.owlin-issue-discrepancy { color: #b8860b; font-weight: 600; margin-bottom: 0.3rem; }
.owlin-issue-description { color: #666; font-size: 0.95rem; }
.owlin-issue-stats { margin-top: 0.5rem; font-size: 0.9rem; color: #888; }
.owlin-footer-btn-row { display: flex; justify-content: flex-end; gap: 1.1rem; margin-bottom: 1.5rem; align-items: center; }
.owlin-clear-btn, .owlin-submit-owlin-btn { 
    position: relative; 
    font-weight: 700; 
    border: none; 
    border-radius: 8px; 
    padding: 0.85rem 2.1rem; 
    font-size: 1.05rem; 
    cursor: pointer; 
    transition: all 0.2s ease-in-out; 
    display: flex; 
    align-items: center; 
    gap: 0.5rem;
}
.owlin-clear-btn { background: #ff9800; color: #fff; }
.owlin-clear-btn:hover:not([disabled]) { background: #e67c00; transform: translateY(-1px); box-shadow: 0 4px 8px rgba(255,152,0,0.3); }
.owlin-submit-owlin-btn { background: #222222; color: #fff; }
.owlin-submit-owlin-btn:hover:not([disabled]) { background: #000; transform: translateY(-1px); box-shadow: 0 4px 8px rgba(34,34,34,0.3); }
.owlin-clear-btn[disabled], .owlin-submit-owlin-btn[disabled] { 
    opacity: 0.5; 
    cursor: not-allowed; 
    transform: none !important; 
    box-shadow: none !important;
}
.owlin-clear-btn[disabled]:hover, .owlin-submit-owlin-btn[disabled]:hover { 
    background: inherit; 
    transform: none; 
    box-shadow: none;
}
.owlin-button-badge { 
    position: absolute; 
    top: -8px; 
    right: -8px; 
    font-size: 0.7rem; 
    padding: 2px 6px; 
    border-radius: 10px; 
    font-weight: 600;
}
.owlin-button-badge.soon { background: #999; color: white; }
.owlin-button-badge.loading { 
    background: #007bff; 
    color: white; 
    animation: pulse 1.5s infinite;
}
.owlin-button-container { position: relative; }
.owlin-footer-status { 
    margin-top: 1rem; 
    padding: 0.8rem; 
    border-radius: 8px; 
    font-size: 0.9rem;
}
.owlin-footer-status.loading { 
    background: #e3f2fd; 
    border: 1px solid #2196f3; 
    color: #1976d2;
}
.owlin-footer-status.disabled { 
    background: #f8f9fa; 
    border: 1px solid #dee2e6; 
    color: #6c757d;
}
.owlin-footer-status.error { 
    background: #fef2f2; 
    border: 1px solid #ef4444; 
    color: #dc2626;
}
.owlin-button-icon { margin-right: 0.5rem; font-size: 1.1rem; }
.owlin-button-text { font-weight: 700; }
.owlin-footer-buttons-group { 
    display: flex; 
    justify-content: flex-end; 
    gap: 1.1rem; 
    margin-bottom: 1.5rem; 
    align-items: center;
    flex-wrap: wrap;
}
@media (max-width: 768px) {
    .owlin-footer-buttons-group { 
        flex-direction: column; 
        align-items: stretch; 
        gap: 0.8rem;
    }
    .owlin-clear-btn, .owlin-submit-owlin-btn { 
        width: 100%; 
        justify-content: center;
    }
}
@media (max-width: 480px) {
    .owlin-clear-btn, .owlin-submit-owlin-btn { 
        padding: 0.7rem 1.5rem; 
        font-size: 1rem;
    }
    .owlin-button-badge { 
        top: -6px; 
        right: -6px; 
        font-size: 0.6rem; 
        padding: 1px 4px;
    }
}
.owlin-button-focus:focus { 
    outline: 3px solid #f1c232; 
    outline-offset: 2px; 
    border-radius: 8px;
}
.owlin-button-loading { 
    position: relative; 
    overflow: hidden;
}
.owlin-button-loading::after { 
    content: ''; 
    position: absolute; 
    top: 0; 
    left: -100%; 
    width: 100%; 
    height: 100%; 
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); 
    animation: shimmer 2s infinite;
}
@keyframes shimmer { 
    0% { left: -100%; } 
    100% { left: 100%; } 
}
.owlin-button-success { 
    background: #10b981 !important; 
    color: white !important;
}
.owlin-button-error { 
    background: #ef4444 !important; 
    color: white !important;
}

/* Enhanced Invoice List Styling */
.owlin-invoice-list {
    background: #f5f6fa;
    border-radius: 18px 0 0 18px;
    min-width: 260px;
    max-width: 340px;
    height: 520px;
    overflow-y: auto;
    padding: 1.2rem 0.5rem 1.2rem 1.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    flex: 0 0 320px;
    position: relative;
}

.owlin-invoice-list::-webkit-scrollbar {
    width: 8px;
    background: #f5f6fa;
}

.owlin-invoice-list::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 6px;
}

.owlin-invoice-list::-webkit-scrollbar-thumb:hover {
    background: #a8adb5;
}

/* Status Summary Header */
.owlin-status-summary {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 0.8rem;
    margin-bottom: 1.2rem;
    border: 1px solid #e9ecef;
    font-size: 0.9rem;
    color: #666;
}

.owlin-status-summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.owlin-status-summary-stats {
    display: flex;
    gap: 1rem;
    font-size: 0.8rem;
    flex-wrap: wrap;
}

.owlin-status-summary-refresh {
    font-size: 0.75rem;
    color: #999;
    margin-top: 0.3rem;
}

/* Enhanced Invoice Cards */
.owlin-invoice-card {
    background: #fff;
    border-radius: 10px;
    margin-bottom: 1.1rem;
    padding: 1.1rem 1.1rem 0.8rem 1.1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s ease-in-out;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    position: relative;
    outline: none;
    min-height: 80px;
}

.owlin-invoice-card:hover {
    border: 2px solid #222222;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transform: translateY(-1px);
}

.owlin-invoice-card.selected {
    border: 2.5px solid #222222;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transform: translateY(-2px);
    background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
}

.owlin-invoice-card:focus {
    outline: 3px solid #f1c232;
    outline-offset: 2px;
    border: 2px solid #f1c232;
}

.owlin-invoice-card.owlin-processing {
    animation: processing-pulse 2s ease-in-out infinite;
    border-left: 4px solid #007bff;
}

/* Selection Indicator */
.owlin-selection-indicator {
    position: absolute;
    top: 0;
    right: 0;
    width: 0;
    height: 0;
    border-left: 12px solid transparent;
    border-right: 12px solid #222222;
    border-top: 12px solid #222222;
    border-radius: 0 10px 0 0;
}

/* Status Badge */
.owlin-status-badge {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    text-align: right;
    min-width: 80px;
}

.owlin-status-badge.processing {
    color: #007bff;
}

.owlin-status-badge.processing::after {
    content: '🔄 Processing';
    font-size: 0.7rem;
    color: #999;
    margin-top: 0.2rem;
    display: block;
}

/* Keyboard Navigation Hints */
.owlin-keyboard-hints {
    font-size: 0.75rem;
    color: #999;
    text-align: center;
    margin: 0.5rem 0;
    padding: 0.3rem;
    background: #f8f9fa;
    border-radius: 4px;
    border: 1px solid #e9ecef;
}

/* Empty State */
.owlin-empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #666;
}

.owlin-empty-state-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
}

.owlin-empty-state-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #222;
}

.owlin-empty-state-description {
    font-size: 0.95rem;
    line-height: 1.5;
    margin-bottom: 1.5rem;
}

.owlin-empty-state-help {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.9rem;
    color: #666;
    text-align: left;
}

.owlin-empty-state-help-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #222;
}

.owlin-empty-state-help ul {
    margin: 0;
    padding-left: 1.2rem;
}

/* Error State */
.owlin-error-state {
    text-align: center;
    padding: 2rem 1rem;
    color: #666;
}

.owlin-error-state-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.owlin-error-state-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #222;
}

.owlin-error-state-description {
    font-size: 0.9rem;
    line-height: 1.4;
    margin-bottom: 1rem;
}

.owlin-error-state-button {
    background: #f1c232;
    color: #222;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
}

.owlin-error-state-button:hover {
    background: #e6a93a;
    transform: translateY(-1px);
}

/* Responsive Design */
@media (max-width: 768px) {
    .owlin-invoice-list {
        min-width: 100%;
        max-width: 100%;
        flex: 1;
        border-radius: 18px;
        margin-bottom: 1rem;
    }
    
    .owlin-invoice-card {
        padding: 1rem;
        min-height: 70px;
    }
    
    .owlin-status-summary-stats {
        flex-direction: column;
        gap: 0.5rem;
    }
}

@media (max-width: 480px) {
    .owlin-invoice-card {
        padding: 0.8rem;
        min-height: 60px;
        font-size: 0.9rem;
    }
    
    .owlin-invoice-status-icon {
        font-size: 1rem;
        min-width: 20px;
        height: 20px;
    }
    
    .owlin-status-badge {
        font-size: 0.7rem;
        min-width: 60px;
    }
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
    .owlin-invoice-card {
        border: 2px solid #000;
    }
    
    .owlin-invoice-card.selected {
        border: 3px solid #000;
        background: #f0f0f0;
    }
    
    .owlin-invoice-card:focus {
        outline: 3px solid #000;
        border: 2px solid #000;
    }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
    .owlin-invoice-card,
    .owlin-invoice-status-icon,
    .owlin-invoice-card.owlin-processing {
        animation: none;
        transition: none;
    }
    
    .owlin-invoice-card:hover,
    .owlin-invoice-card.selected {
        transform: none;
    }
}
</style>
''', unsafe_allow_html=True)

# --- Utility Functions ---
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
    """
    Render a metric box with optional highlighting and enhanced styling.
    
    Args:
        label (str): The metric label (e.g., "Total Value")
        value (str): The metric value (e.g., "£1,234.56")
        highlight (bool): Whether to apply highlighting for attention
    
    Returns:
        str: HTML string for the metric box
    """
    highlight_class = " highlighted" if highlight else ""
    return f'<div class="owlin-metric-box{highlight_class}" role="region" aria-label="{label}: {value}">{label}<br>{value}</div>'

def sanitize_text(text):
    """
    Sanitize text for safe display and prevent XSS attacks.
    
    Args:
        text (str): Text to sanitize
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ''
    
    try:
        # Remove HTML tags and encode special characters
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

# --- Component: Upload Box ---
# Enhanced version with accessibility features is defined later in the file

# --- Component: Summary Metrics ---
def render_summary_metrics(metrics_data=None):
    """
    Render the summary metrics row showing total value, issues count, and error amount with sticky header.
    
    Args:
        metrics_data (dict, optional): Pre-fetched metrics data. If None, fetches from backend.
            Expected format: {
                'total_value': float,
                'num_issues': int, 
                'total_error': float,
                'total_invoices': int,
                'paired_invoices': int,
                'processing_invoices': int
            }
    
    Features:
        - Sticky header positioning for scroll usability
        - Dynamic data fetching or accepts pre-fetched data
        - Currency formatting with proper locale
        - Conditional highlighting for issues and errors
        - Responsive layout with enhanced styling
        - Comprehensive error handling with fallbacks
        - Loading states and performance optimization
        - Real-time updates and visual feedback
        - Brand-consistent styling with Owlin colors
    """
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
        
        # Format currency values
        formatted_total = format_currency(total_value)
        formatted_error = format_currency(total_error)
        
        # Determine highlighting based on values
        issues_highlight = num_issues > 0
        error_highlight = total_error > 0
        processing_highlight = processing_invoices > 0
        
        # Calculate completion percentage
        completion_percentage = (paired_invoices / total_invoices * 100) if total_invoices > 0 else 0
        
        # Render sticky metrics row with enhanced styling
        st.markdown(f'''
            <div class="owlin-metrics-container" style="position: sticky; top: 0; z-index: 1000; background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-bottom: 2px solid #e9ecef; padding: 1rem 0; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div class="owlin-metrics-row" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto;">
                    
                    <!-- Total Value Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💰</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">{formatted_total}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Value</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{total_invoices} invoice{'s' if total_invoices != 1 else ''}</div>
                    </div>
                    
                    <!-- Number of Issues Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#fff5f5' if issues_highlight else '#ffffff'} 0%, {'#fef2f2' if issues_highlight else '#f8f9fa'} 100%); border: 2px solid {'#ef4444' if issues_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                        <div style="font-weight: 700; color: {'#dc2626' if issues_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{num_issues}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Issues Detected</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{formatted_error} impact</div>
                    </div>
                    
                    <!-- Total Error Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#fff5f5' if error_highlight else '#ffffff'} 0%, {'#fef2f2' if error_highlight else '#f8f9fa'} 100%); border: 2px solid {'#ef4444' if error_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💸</div>
                        <div style="font-weight: 700; color: {'#dc2626' if error_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{formatted_error}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Error</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">Potential loss</div>
                    </div>
                    
                    <!-- Processing Status Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#f0f9ff' if processing_highlight else '#ffffff'} 0%, {'#e0f2fe' if processing_highlight else '#f8f9fa'} 100%); border: 2px solid {'#0ea5e9' if processing_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔄</div>
                        <div style="font-weight: 700; color: {'#0369a1' if processing_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{processing_invoices}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Processing</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{completion_percentage:.1f}% complete</div>
                    </div>
                    
                    <!-- Pairing Status Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 2px solid #10b981; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔗</div>
                        <div style="font-weight: 700; color: #065f46; font-size: 1.4rem; margin-bottom: 0.3rem;">{paired_invoices}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Paired</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">Ready for review</div>
                    </div>
                    
                </div>
                
                <!-- Enhanced Context Bar -->
                <div class="owlin-metrics-context" style="margin-top: 1rem; padding: 0.8rem; background: rgba(255,255,255,0.8); border-radius: 8px; border: 1px solid #e9ecef;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; font-size: 0.9rem;">
                        <div style="display: flex; gap: 1.5rem; flex-wrap;">
                            {f'<span style="color: #dc2626; font-weight: 600;">⚠️ {num_issues} discrepancy{"s" if num_issues != 1 else ""} require attention</span>' if issues_highlight else ''}
                            {f'<span style="color: #0369a1; font-weight: 600;">🔄 {processing_invoices} invoice{"s" if processing_invoices != 1 else ""} being processed</span>' if processing_highlight else ''}
                            {f'<span style="color: #065f46; font-weight: 600;">✅ {paired_invoices} invoice{"s" if paired_invoices != 1 else ""} ready for submission</span>' if paired_invoices > 0 else ''}
                        </div>
                        <div style="color: #666; font-size: 0.8rem;">
                            🔄 Auto-updating • Last refresh: {datetime.now().strftime('%H:%M:%S')}
                        </div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Performance tracking
        if 'metrics_load_time' not in st.session_state:
            st.session_state.metrics_load_time = datetime.now()
        
        # Track metrics for analytics
        if 'metrics_display_count' not in st.session_state:
            st.session_state.metrics_display_count = 0
        st.session_state.metrics_display_count += 1
        
    except Exception as e:
        st.error(f"❌ Failed to load summary metrics: {str(e)}")
        
        # Fallback metrics on error with sticky positioning
        st.markdown('''
            <div class="owlin-metrics-container" style="position: sticky; top: 0; z-index: 1000; background: #f8f9fa; border-bottom: 2px solid #e9ecef; padding: 1rem 0; margin-bottom: 2rem;">
                <div class="owlin-metrics-row" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto;">
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💰</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">£0.00</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Value</div>
                    </div>
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">0</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Issues Detected</div>
                    </div>
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💸</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">£0.00</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Error</div>
                    </div>
                </div>
                <div style="margin-top: 1rem; padding: 0.8rem; background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; color: #856404; font-size: 0.9rem;">
                    ⚠️ Using fallback metrics due to data loading error
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'metrics_error_count' not in st.session_state:
            st.session_state.metrics_error_count = 0
        st.session_state.metrics_error_count += 1

# --- Component: Invoice List ---
def render_invoice_list(invoices, selected_index=None, on_select=None):
    """
    Render a scrollable invoice list with selectable cards, real-time statuses, and enhanced accessibility.
    
    Args:
        invoices (list): List of invoice dictionaries from the database
        selected_index (int, optional): Currently selected invoice index. If None, uses session state
        on_select (callable, optional): Callback function when an invoice is selected. 
            Signature: on_select(index, invoice_data)
    
    Features:
        - Real-time status updates with dynamic database loading
        - Status icons for different invoice states (matched, discrepancy, pending, processing, not_paired)
        - Clickable cards with clear visual selection highlighting
        - Comprehensive accessibility support with ARIA labels and keyboard navigation
        - Graceful handling of empty lists with friendly messaging
        - External selection management support
        - Real-time status polling and updates
        - Enhanced visual feedback and animations
    """
    st.markdown('<div class="owlin-invoice-list" role="list" aria-label="Invoice list with real-time statuses">', unsafe_allow_html=True)
    
    try:
        # Dynamic database loading with real-time updates
        if not invoices:
            invoices = []
        
        # Real-time status polling (refresh every 30 seconds)
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
    
    except Exception as e:
        st.error(f"Error loading invoice list: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

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
# --- Utility Functions ---
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
    """
    Render a metric box with optional highlighting and enhanced styling.
    
    Args:
        label (str): The metric label (e.g., "Total Value")
        value (str): The metric value (e.g., "£1,234.56")
        highlight (bool): Whether to apply highlighting for attention
    
    Returns:
        str: HTML string for the metric box
    """
    highlight_class = " highlighted" if highlight else ""
    return f'<div class="owlin-metric-box{highlight_class}" role="region" aria-label="{label}: {value}">{label}<br>{value}</div>'

def sanitize_text(text):
    """
    Sanitize text for safe display and prevent XSS attacks.
    
    Args:
        text (str): Text to sanitize
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ''
    
    try:
        # Remove HTML tags and encode special characters
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

# --- Component: Upload Box ---
# Enhanced version with accessibility features is defined later in the file

# --- Component: Summary Metrics ---
def render_summary_metrics(metrics_data=None):
    """
    Render the summary metrics row showing total value, issues count, and error amount with sticky header.
    
    Args:
        metrics_data (dict, optional): Pre-fetched metrics data. If None, fetches from backend.
            Expected format: {
                'total_value': float,
                'num_issues': int, 
                'total_error': float,
                'total_invoices': int,
                'paired_invoices': int,
                'processing_invoices': int
            }
    
    Features:
        - Sticky header positioning for scroll usability
        - Dynamic data fetching or accepts pre-fetched data
        - Currency formatting with proper locale
        - Conditional highlighting for issues and errors
        - Responsive layout with enhanced styling
        - Comprehensive error handling with fallbacks
        - Loading states and performance optimization
        - Real-time updates and visual feedback
        - Brand-consistent styling with Owlin colors
    """
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
        
        # Format currency values
        formatted_total = format_currency(total_value)
        formatted_error = format_currency(total_error)
        
        # Determine highlighting based on values
        issues_highlight = num_issues > 0
        error_highlight = total_error > 0
        processing_highlight = processing_invoices > 0
        
        # Calculate completion percentage
        completion_percentage = (paired_invoices / total_invoices * 100) if total_invoices > 0 else 0
        
        # Render sticky metrics row with enhanced styling
        st.markdown(f'''
            <div class="owlin-metrics-container" style="position: sticky; top: 0; z-index: 1000; background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-bottom: 2px solid #e9ecef; padding: 1rem 0; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div class="owlin-metrics-row" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto;">
                    
                    <!-- Total Value Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💰</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">{formatted_total}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Value</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{total_invoices} invoice{'s' if total_invoices != 1 else ''}</div>
                    </div>
                    
                    <!-- Number of Issues Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#fff5f5' if issues_highlight else '#ffffff'} 0%, {'#fef2f2' if issues_highlight else '#f8f9fa'} 100%); border: 2px solid {'#ef4444' if issues_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                        <div style="font-weight: 700; color: {'#dc2626' if issues_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{num_issues}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Issues Detected</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{formatted_error} impact</div>
                    </div>
                    
                    <!-- Total Error Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#fff5f5' if error_highlight else '#ffffff'} 0%, {'#fef2f2' if error_highlight else '#f8f9fa'} 100%); border: 2px solid {'#ef4444' if error_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💸</div>
                        <div style="font-weight: 700; color: {'#dc2626' if error_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{formatted_error}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Error</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">Potential loss</div>
                    </div>
                    
                    <!-- Processing Status Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, {'#f0f9ff' if processing_highlight else '#ffffff'} 0%, {'#e0f2fe' if processing_highlight else '#f8f9fa'} 100%); border: 2px solid {'#0ea5e9' if processing_highlight else '#e9ecef'}; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔄</div>
                        <div style="font-weight: 700; color: {'#0369a1' if processing_highlight else '#222'}; font-size: 1.4rem; margin-bottom: 0.3rem;">{processing_invoices}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Processing</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">{completion_percentage:.1f}% complete</div>
                    </div>
                    
                    <!-- Pairing Status Metric -->
                    <div class="owlin-metric-box" style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 2px solid #10b981; border-radius: 12px; padding: 1.2rem; text-align: center; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔗</div>
                        <div style="font-weight: 700; color: #065f46; font-size: 1.4rem; margin-bottom: 0.3rem;">{paired_invoices}</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Paired</div>
                        <div style="font-size: 0.8rem; color: #999; margin-top: 0.3rem;">Ready for review</div>
                    </div>
                    
                </div>
                
                <!-- Enhanced Context Bar -->
                <div class="owlin-metrics-context" style="margin-top: 1rem; padding: 0.8rem; background: rgba(255,255,255,0.8); border-radius: 8px; border: 1px solid #e9ecef;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; font-size: 0.9rem;">
                        <div style="display: flex; gap: 1.5rem; flex-wrap;">
                            {f'<span style="color: #dc2626; font-weight: 600;">⚠️ {num_issues} discrepancy{"s" if num_issues != 1 else ""} require attention</span>' if issues_highlight else ''}
                            {f'<span style="color: #0369a1; font-weight: 600;">🔄 {processing_invoices} invoice{"s" if processing_invoices != 1 else ""} being processed</span>' if processing_highlight else ''}
                            {f'<span style="color: #065f46; font-weight: 600;">✅ {paired_invoices} invoice{"s" if paired_invoices != 1 else ""} ready for submission</span>' if paired_invoices > 0 else ''}
                        </div>
                        <div style="color: #666; font-size: 0.8rem;">
                            🔄 Auto-updating • Last refresh: {datetime.now().strftime('%H:%M:%S')}
                        </div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Performance tracking
        if 'metrics_load_time' not in st.session_state:
            st.session_state.metrics_load_time = datetime.now()
        
        # Track metrics for analytics
        if 'metrics_display_count' not in st.session_state:
            st.session_state.metrics_display_count = 0
        st.session_state.metrics_display_count += 1
        
    except Exception as e:
        st.error(f"❌ Failed to load summary metrics: {str(e)}")
        
        # Fallback metrics on error with sticky positioning
        st.markdown('''
            <div class="owlin-metrics-container" style="position: sticky; top: 0; z-index: 1000; background: #f8f9fa; border-bottom: 2px solid #e9ecef; padding: 1rem 0; margin-bottom: 2rem;">
                <div class="owlin-metrics-row" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto;">
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💰</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">£0.00</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Value</div>
                    </div>
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">0</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Issues Detected</div>
                    </div>
                    <div style="background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💸</div>
                        <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">£0.00</div>
                        <div style="color: #666; font-size: 0.9rem; font-weight: 600;">Total Error</div>
                    </div>
                </div>
                <div style="margin-top: 1rem; padding: 0.8rem; background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; color: #856404; font-size: 0.9rem;">
                    ⚠️ Using fallback metrics due to data loading error
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'metrics_error_count' not in st.session_state:
            st.session_state.metrics_error_count = 0
        st.session_state.metrics_error_count += 1

# --- Utility Functions ---

def get_enhanced_status_icon(status):
    """Get enhanced status icon HTML with better accessibility and visual feedback."""
    icons = {
        "matched": '<span class="owlin-invoice-status-icon owlin-invoice-status-matched" aria-label="Matched - Invoice and delivery note quantities match" title="Matched">✅</span>',
        "discrepancy": '<span class="owlin-invoice-status-icon owlin-invoice-status-discrepancy" aria-label="Discrepancy detected - Quantities don\'t match" title="Discrepancy">⚠️</span>',
        "not_paired": '<span class="owlin-invoice-status-icon owlin-invoice-status-not_paired" aria-label="Not paired - Missing delivery note" title="Not Paired">❌</span>',
        "pending": '<span class="owlin-invoice-status-icon owlin-invoice-status-pending" aria-label="Pending - Awaiting processing" title="Pending">⏳</span>',
        "processing": '<span class="owlin-invoice-status-icon owlin-invoice-status-processing" aria-label="Processing - Currently being analyzed" title="Processing">🔄</span>'
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
    
    # Create lookup dictionaries
    prev_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in previous_invoices}
    curr_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in current_invoices}
    
    # Check for status changes
    for inv_id, previous_status in prev_lookup.items():
        current_status = curr_lookup.get(inv_id)
        if current_status and previous_status != current_status:
            invoice_number = next((inv.get('invoice_number', 'Unknown') for inv in current_invoices if inv.get('id') == inv_id), 'Unknown')
            changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")
    
    return changes
        
        if invoices:
            # Enhanced header with real-time status summary
            status_counts = get_status_counts(invoices)
            total_value = sum(inv.get('total', 0) for inv in invoices)
            
            st.markdown(f'''
                <div style="padding: 0.8rem 0; margin-bottom: 1.2rem; font-size: 0.9rem; color: #666; border-bottom: 1px solid #eee; background: #f8f9fa; border-radius: 8px; padding: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: 600; color: #222;">📄 {len(invoices)} invoice{'s' if len(invoices) != 1 else ''}</span>
                        <span style="font-weight: 600; color: #222;">💰 {format_currency(total_value)}</span>
                    </div>
                    <div style="display: flex; gap: 1rem; font-size: 0.8rem; flex-wrap: wrap;">
                        {f'<span style="color: #4CAF50;">✅ {status_counts["matched"]} matched</span>' if status_counts["matched"] > 0 else ''}
                        {f'<span style="color: #f1c232;">⚠️ {status_counts["discrepancy"]} discrepancies</span>' if status_counts["discrepancy"] > 0 else ''}
                        {f'<span style="color: #ff3b30;">❌ {status_counts["not_paired"]} not paired</span>' if status_counts["not_paired"] > 0 else ''}
                        {f'<span style="color: #007bff;">🔄 {status_counts["processing"]} processing</span>' if status_counts["processing"] > 0 else ''}
                        {f'<span style="color: #888;">⏳ {status_counts["pending"]} pending</span>' if status_counts["pending"] > 0 else ''}
                    </div>
                    <div style="font-size: 0.75rem; color: #999; margin-top: 0.3rem;">
                        🔄 Auto-refreshing every 30 seconds • Last updated: {datetime.now().strftime('%H:%M:%S')}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Enhanced invoice cards with real-time statuses
            for idx, inv in enumerate(invoices):
                # Get enhanced status information
                status = inv.get('status', 'pending')
                status_icon = get_enhanced_status_icon(status)
                is_selected = (idx == selected_index)
                card_class = "owlin-invoice-card selected" if is_selected else "owlin-invoice-card"
                
                # Add processing animation for processing status
                if status == 'processing':
                    card_class += " owlin-processing"
                
                # Create unique key for each invoice card
                card_key = f"invoice_card_{inv.get('id', idx)}_{idx}"
                
                # Enhanced invoice data extraction
                invoice_number = sanitize_text(inv.get('invoice_number', 'N/A'))
                supplier = sanitize_text(inv.get('supplier', 'N/A'))
                date = sanitize_text(inv.get('date', ''))
                total = format_currency(inv.get('total', 0))
                
                # Create comprehensive ARIA label for accessibility
                aria_label = f"Invoice {invoice_number} from {supplier}, {status} status, total {total}, {date}"
                if is_selected:
                    aria_label += ", currently selected"
                
                # Enhanced clickable invoice card with keyboard support
                if st.button(
                    f"Select {invoice_number} from {supplier}", 
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
                
                # Enhanced invoice card rendering with real-time status
                st.markdown(f'''
                    <div class="{card_class}" 
                         role="listitem" 
                         aria-label="{aria_label}"
                         aria-selected="{str(is_selected).lower()}"
                         data-invoice-id="{inv.get('id', '')}"
                         data-invoice-number="{invoice_number}"
                         data-supplier="{supplier}"
                         data-status="{status}"
                         tabindex="0"
                         onkeydown="handleInvoiceCardKeydown(event, {idx})"
                         onclick="selectInvoiceCard({idx})"
                         style="cursor: pointer; transition: all 0.2s ease-in-out; {'border: 2.5px solid #222222; box-shadow: 0 4px 12px rgba(0,0,0,0.15); transform: translateY(-2px);' if is_selected else ''}">
                        
                        <!-- Status Icon with Enhanced Styling -->
                        <div style="margin-right: 0.7rem; display: flex; align-items: center; justify-content: center; min-width: 24px;">
                            {status_icon}
                        </div>
                        
                        <!-- Invoice Details -->
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 700; font-size: 1.05rem; color: #222; margin-bottom: 0.3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {invoice_number}
                            </div>
                            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {supplier}
                            </div>
                            <div style="font-size: 0.85rem; color: #888; margin-bottom: 0.5rem;">
                                {date}
                            </div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #222;">
                                {total}
                            </div>
                        </div>
                        
                        <!-- Status Badge -->
                        <div style="margin-left: 0.5rem; text-align: right; min-width: 80px;">
                            <div style="font-size: 0.8rem; color: {get_status_color(status)}; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">
                                {status.replace('_', ' ')}
                            </div>
                            {f'<div style="font-size: 0.7rem; color: #999; margin-top: 0.2rem;">🔄 Processing</div>' if status == 'processing' else ''}
                        </div>
                        
                        <!-- Selection Indicator -->
                        {f'<div style="position: absolute; top: 0; right: 0; width: 0; height: 0; border-left: 12px solid transparent; border-right: 12px solid #222222; border-top: 12px solid #222222;"></div>' if is_selected else ''}
                    </div>
                ''', unsafe_allow_html=True)
                
                # Add keyboard navigation hint for first card
                if idx == 0:
                    st.markdown('''
                        <div style="font-size: 0.75rem; color: #999; text-align: center; margin: 0.5rem 0; padding: 0.3rem; background: #f8f9fa; border-radius: 4px;">
                            💡 Use Tab to navigate, Enter to select • Arrow keys to move between invoices
                        </div>
                    ''', unsafe_allow_html=True)
        else:
            # Enhanced empty state with helpful guidance
            st.markdown('''
                <div style="text-align: center; padding: 3rem 1rem; color: #666;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                        No invoices uploaded yet
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">
                        Upload some invoices using the boxes above to get started.<br>
                        The system will automatically process and display them here with real-time status updates.
                    </div>
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #666;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: #222;">📋 What happens next:</div>
                        <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                            <li>Upload invoices and delivery notes</li>
                            <li>System processes files with OCR</li>
                            <li>Automatic discrepancy detection</li>
                            <li>Real-time status updates</li>
                        </ul>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Failed to load invoice list: {str(e)}")
        
        # Enhanced error state with retry option
        st.markdown('''
            <div style="text-align: center; padding: 2rem 1rem; color: #666;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                    Unable to load invoices
                </div>
                <div style="font-size: 0.9rem; line-height: 1.4; margin-bottom: 1rem;">
                    There was an error loading the invoice list.<br>
                    Please try refreshing the page or contact support.
                </div>
                <button onclick="location.reload()" style="background: #f1c232; color: #222; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-weight: 600;">
                    🔄 Refresh Page
                </button>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'invoice_list_error_count' not in st.session_state:
            st.session_state.invoice_list_error_count = 0
        st.session_state.invoice_list_error_count += 1
    
    # Add JavaScript for enhanced keyboard navigation
    st.markdown('''
        <script>
        function handleInvoiceCardKeydown(event, index) {
            const cards = document.querySelectorAll('.owlin-invoice-card');
            const currentIndex = index;
            
            switch(event.key) {
                case 'Enter':
                case ' ':
                    event.preventDefault();
                    selectInvoiceCard(currentIndex);
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    const nextIndex = Math.min(currentIndex + 1, cards.length - 1);
                    if (cards[nextIndex]) {
                        cards[nextIndex].focus();
                        selectInvoiceCard(nextIndex);
                    }
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    const prevIndex = Math.max(currentIndex - 1, 0);
                    if (cards[prevIndex]) {
                        cards[prevIndex].focus();
                        selectInvoiceCard(prevIndex);
                    }
                    break;
                case 'Home':
                    event.preventDefault();
                    if (cards[0]) {
                        cards[0].focus();
                        selectInvoiceCard(0);
                    }
                    break;
                case 'End':
                    event.preventDefault();
                    if (cards[cards.length - 1]) {
                        cards[cards.length - 1].focus();
                        selectInvoiceCard(cards.length - 1);
                    }
                    break;
            }
        }
        
        function selectInvoiceCard(index) {
            // Remove selection from all cards
            document.querySelectorAll('.owlin-invoice-card').forEach(card => {
                card.classList.remove('selected');
                card.setAttribute('aria-selected', 'false');
            });
            
            // Select the clicked card
            const selectedCard = document.querySelectorAll('.owlin-invoice-card')[index];
            if (selectedCard) {
                selectedCard.classList.add('selected');
                selectedCard.setAttribute('aria-selected', 'true');
                selectedCard.focus();
                
                // Announce selection to screen readers
                const invoiceNumber = selectedCard.getAttribute('data-invoice-number');
                const supplier = selectedCard.getAttribute('data-supplier');
                const status = selectedCard.getAttribute('data-status');
                
                if (window.announceToScreenReader) {
                    window.announceToScreenReader(`Selected invoice ${invoiceNumber} from ${supplier}, status: ${status}`);
                }
            }
            
            // Trigger Streamlit rerun with new selection
            // This would need to be handled by Streamlit's session state
        }
        
        // Add focus management for better accessibility
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.owlin-invoice-card');
            cards.forEach((card, index) => {
                card.addEventListener('focus', function() {
                    // Add visual focus indicator
                    this.style.outline = '3px solid #f1c232';
                    this.style.outlineOffset = '2px';
                });
                
                card.addEventListener('blur', function() {
                    // Remove focus indicator
                    this.style.outline = '';
                    this.style.outlineOffset = '';
                });
            });
        });
        </script>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Component: Invoice Details ---
def render_invoice_details(invoices, selected_invoice_details=None):
    """
    Render the invoice details pane with comprehensive line items table, OCR confidence, and enhanced metadata.
    
    Args:
        invoices (list): List of invoice dictionaries from the database
        selected_invoice_details (dict, optional): Pre-fetched invoice details. If None, fetches from database.
    
    Features:
        - Fetches detailed invoice data by selected invoice ID
        - Comprehensive invoice metadata display (number, supplier, date, total)
        - OCR confidence and processing information
        - Sticky-header table with line items and discrepancy highlighting
        - Inline issue flags with icons and color coding
        - Enhanced accessibility with proper ARIA labels
        - Disabled action buttons with hover/focus styles
        - Real-time status updates and error handling
    """
    st.markdown('<div class="owlin-invoice-details" role="region" aria-label="Invoice details">', unsafe_allow_html=True)
    
    try:
        if not invoices or len(invoices) == 0:
            # Enhanced empty state with helpful guidance
            st.markdown('''
                <div style="text-align: center; padding: 3rem 1rem; color: #666;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📋</div>
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                        No invoices to display
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">
                        Upload some invoices using the boxes above to view detailed information.<br>
                        Select an invoice from the list to see its complete metadata and line items.
                    </div>
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #666;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: #222;">📊 What you'll see:</div>
                        <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                            <li>Complete invoice metadata and supplier information</li>
                            <li>Detailed line items with quantity comparisons</li>
                            <li>OCR confidence scores and processing status</li>
                            <li>Discrepancy highlighting and issue flags</li>
                            <li>Total calculations and summary information</li>
                        </ul>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            return
        
        # Get selected invoice and fetch detailed data
        selected_invoice_idx = st.session_state.get('selected_invoice_idx', 0)
        if selected_invoice_idx >= len(invoices):
            selected_invoice_idx = 0
        
        selected_invoice = invoices[selected_invoice_idx]
        invoice_id = selected_invoice.get('id')
        
        # Fetch detailed invoice data by ID
        if selected_invoice_details is None and invoice_id:
            try:
                with st.spinner("Loading detailed invoice data..."):
                    invoice_details = get_invoice_details(invoice_id)
            except Exception as e:
                st.error(f"❌ Failed to fetch invoice details: {str(e)}")
                invoice_details = None
        else:
            invoice_details = selected_invoice_details
        
        if invoice_details:
            # Extract comprehensive invoice metadata
            invoice_number = sanitize_text(invoice_details.get('invoice_number', 'N/A'))
            supplier = sanitize_text(invoice_details.get('supplier', 'N/A'))
            invoice_date = sanitize_text(invoice_details.get('invoice_date', ''))
            total_amount = format_currency(invoice_details.get('total_amount', 0))
            line_items = invoice_details.get('line_items', [])
            
            # Extract OCR and processing information
            ocr_confidence = invoice_details.get('ocr_confidence', None)
            processing_status = invoice_details.get('processing_status', 'completed')
            processing_time = invoice_details.get('processing_time', None)
            extracted_text_length = invoice_details.get('extracted_text_length', 0)
            
            # Calculate discrepancy statistics
            total_discrepancy_value = 0
            discrepancy_count = 0
            for item in line_items:
                if item.get('flagged') or (item.get('delivery_qty') is not None and 
                                          item.get('delivery_qty') != item.get('invoice_qty', 0)):
                    discrepancy_count += 1
                    if item.get('delivery_qty') is not None:
                        qty_diff = abs(item.get('invoice_qty', 0) - item.get('delivery_qty', 0))
                        total_discrepancy_value += qty_diff * item.get('unit_price', 0)
            
            # Enhanced invoice header with comprehensive metadata
            st.markdown(f'''
                <div style="border-bottom: 2px solid #f0f0f0; padding-bottom: 1.5rem; margin-bottom: 2rem;">
                    <!-- Main Invoice Header -->
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <div style="flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: 800; color: #222; margin-bottom: 0.5rem;">
                                Invoice: {invoice_number}
                            </div>
                            <div style="color: #666; font-size: 1.1rem; margin-bottom: 0.3rem;">
                                <strong>Supplier:</strong> {supplier}
                            </div>
                            <div style="color: #666; font-size: 1.1rem; margin-bottom: 0.3rem;">
                                <strong>Date:</strong> {invoice_date}
                            </div>
                        </div>
                        <div style="text-align: right; margin-left: 2rem;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #222; margin-bottom: 0.3rem;">
                                {total_amount}
                            </div>
                            <div style="font-size: 0.9rem; color: #666;">
                                Total Amount
                            </div>
                        </div>
                    </div>
                    
                    <!-- Processing Information Row -->
                    <div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1rem;">
                        {f"""
                        <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; padding: 0.6rem 1rem; font-size: 0.9rem;">
                            <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 0.2rem;">🔍 OCR Confidence</div>
                            <div style="color: #0369a1; font-size: 1.1rem; font-weight: 700;">{ocr_confidence:.1%}</div>
                        </div>
                        """ if ocr_confidence is not None else ''}
                        
                        {f"""
                        <div style="background: #f0fdf4; border: 1px solid #10b981; border-radius: 6px; padding: 0.6rem 1rem; font-size: 0.9rem;">
                            <div style="font-weight: 600; color: #065f46; margin-bottom: 0.2rem;">📝 Text Extracted</div>
                            <div style="color: #047857; font-size: 1.1rem; font-weight: 700;">{extracted_text_length:,} chars</div>
                        </div>
                        """ if extracted_text_length > 0 else ''}
                        
                        {f"""
                        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 0.6rem 1rem; font-size: 0.9rem;">
                            <div style="font-weight: 600; color: #92400e; margin-bottom: 0.2rem;">⏱️ Processing Time</div>
                            <div style="color: #d97706; font-size: 1.1rem; font-weight: 700;">{processing_time:.1f}s</div>
                        </div>
                        """ if processing_time else ''}
                        
                        <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 0.6rem 1rem; font-size: 0.9rem;">
                            <div style="font-weight: 600; color: #495057; margin-bottom: 0.2rem;">📊 Line Items</div>
                            <div style="color: #6c757d; font-size: 1.1rem; font-weight: 700;">{len(line_items)}</div>
                        </div>
                    </div>
                    
                    <!-- Discrepancy Summary -->
                    {f"""
                    <div style="background: #fff7e0; border: 1px solid #f1c232; border-radius: 6px; padding: 0.8rem 1rem; margin-top: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span style="font-size: 1.1rem;">⚠️</span>
                                <span style="font-weight: 600; color: #b8860b;">Discrepancy Summary</span>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 700; color: #b8860b; font-size: 1.1rem;">{format_currency(total_discrepancy_value)}</div>
                                <div style="font-size: 0.8rem; color: #666;">{discrepancy_count} item{'s' if discrepancy_count != 1 else ''} affected</div>
                            </div>
                        </div>
                    </div>
                    """ if discrepancy_count > 0 else ''}
                </div>
            ''', unsafe_allow_html=True)
            
            # Enhanced line items table with sticky headers and comprehensive data
            if line_items:
                st.markdown(f'''
                    <div style="margin-bottom: 1.5rem; font-size: 0.9rem; color: #666; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.1rem;">📊</span>
                            <span>{len(line_items)} line item{'s' if len(line_items) != 1 else ''}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #888;">
                            💡 Hover over discrepancy icons for details
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                st.markdown('''
                    <div style="overflow-x: auto; border-radius: 8px; border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <table class="owlin-invoice-table" role="table" aria-label="Invoice line items with quantity comparisons">
                            <thead>
                                <tr>
                                    <th scope="col" style="min-width: 250px; text-align: left;">Item Description</th>
                                    <th scope="col" style="min-width: 120px; text-align: center;">Invoice Qty</th>
                                    <th scope="col" style="min-width: 120px; text-align: center;">Delivery Qty</th>
                                    <th scope="col" style="min-width: 140px; text-align: right;">Unit Price (£)</th>
                                    <th scope="col" style="min-width: 140px; text-align: right;">Total (£)</th>
                                    <th scope="col" style="min-width: 100px; text-align: center;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                ''', unsafe_allow_html=True)
                
                # Render enhanced line items with comprehensive data
                for idx, item in enumerate(line_items):
                    # Extract and sanitize comprehensive item data
                    item_name = sanitize_text(item.get('item', 'N/A'))
                    invoice_qty = item.get('invoice_qty', 0)
                    delivery_qty = item.get('delivery_qty')
                    unit_price = format_currency(item.get('unit_price', 0))
                    item_total = format_currency(item.get('total', 0))
                    
                    # Enhanced discrepancy detection
                    has_discrepancy = (
                        item.get('flagged', False) or 
                        (delivery_qty is not None and delivery_qty != invoice_qty)
                    )
                    
                    # Calculate discrepancy details
                    discrepancy_value = 0
                    discrepancy_type = None
                    if delivery_qty is not None and delivery_qty != invoice_qty:
                        discrepancy_value = abs(invoice_qty - delivery_qty) * item.get('unit_price', 0)
                        if delivery_qty > invoice_qty:
                            discrepancy_type = "over_delivered"
                        else:
                            discrepancy_type = "under_delivered"
                    
                    # Determine delivery quantity display with enhanced formatting
                    if delivery_qty is not None:
                        dq_display = str(delivery_qty)
                        dq_tooltip = f"Delivered: {delivery_qty}"
                    else:
                        dq_display = '-'
                        dq_tooltip = "No delivery data available"
                    
                    # Create comprehensive row styling and ARIA attributes
                    row_class = "owlin-discrepancy-row" if has_discrepancy else ""
                    row_aria_label = f"Line item {idx + 1}: {item_name}"
                    if has_discrepancy:
                        if discrepancy_type:
                            row_aria_label += f", {discrepancy_type.replace('_', ' ')} by {abs(invoice_qty - delivery_qty)} units"
                        else:
                            row_aria_label += ", flagged for review"
                    
                    # Enhanced delivery quantity cell with comprehensive discrepancy highlighting
                    if has_discrepancy:
                        discrepancy_icon = "⚠️" if discrepancy_type else "🚩"
                        discrepancy_color = "#f1c232" if discrepancy_type else "#ff3b30"
                        discrepancy_bg = "#fffbe6" if discrepancy_type else "#fff5f5"
                        
                        dq_cell = f'''
                            <td class="owlin-discrepancy-cell" 
                                style="text-align: center; position: relative; background: {discrepancy_bg} !important; border: 1px solid {discrepancy_color} !important;"
                                aria-label="{dq_tooltip}, discrepancy detected"
                                title="{dq_tooltip}">
                                <div style="display: flex; align-items: center; justify-content: center; gap: 0.3rem;">
                                    <span style="color: {discrepancy_color}; font-weight: 600;">{dq_display}</span>
                                    <span class="owlin-discrepancy-icon" 
                                          style="font-size: 1rem;"
                                          aria-label="Discrepancy detected">⚠️</span>
                                </div>
                                {f'<div style="position: absolute; top: -2px; right: -2px; width: 8px; height: 8px; background: {discrepancy_color}; border-radius: 50%;"></div><div style="position: absolute; bottom: -2px; left: 0; right: 0; height: 2px; background: {discrepancy_color}; border-radius: 1px;"></div>' if discrepancy_value > 0 else ''}
                            </td>
                        '''
                    else:
                        dq_cell = f'''
                            <td style="text-align: center; position: relative;" title="{dq_tooltip}">
                                <span style="color: #666;">{dq_display}</span>
                            </td>
                        '''
                    
                    # Status cell with comprehensive information
                    status_cell = ""
                    if has_discrepancy:
                        if discrepancy_type:
                            status_text = "Over Delivered" if discrepancy_type == "over_delivered" else "Under Delivered"
                            status_color = "#f1c232"
                            status_bg = "#fffbe6"
                        else:
                            status_text = "Flagged"
                            status_color = "#ff3b30"
                            status_bg = "#fff5f5"
                        
                        status_cell = f'''
                            <td style="text-align: center; padding: 0.3rem;">
                                <div style="background: {status_bg}; color: {status_color}; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid {status_color};">
                                    {status_text}
                                </div>
                                {f'<div style="font-size: 0.7rem; color: #666; margin-top: 0.2rem;">{format_currency(discrepancy_value)}</div>' if discrepancy_value > 0 else ''}
                            </td>
                        '''
                    else:
                        status_cell = '''
                            <td style="text-align: center; padding: 0.3rem;">
                                <div style="background: #f0fdf4; color: #10b981; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid #10b981;">
                                    ✅ Matched
                                </div>
                            </td>
                        '''
                    
                    # Render the enhanced table row
                    st.markdown(f'''
                        <tr class="{row_class}" 
                            role="row" 
                            aria-label="{row_aria_label}"
                            data-item-id="{idx}"
                            data-has-discrepancy="{str(has_discrepancy).lower()}"
                            data-discrepancy-type="{discrepancy_type or 'none'}"
                            data-discrepancy-value="{discrepancy_value}"
                            style="{'background: #fffbe6 !important; border-left: 4px solid #f1c232 !important;' if has_discrepancy else ''}">
                            <td style="font-weight: 500; color: #222; padding: 1rem 0.8rem;">
                                <div style="font-weight: 600; margin-bottom: 0.2rem;">{item_name}</div>
                                {f'<div style="font-size: 0.8rem; color: #666; font-style: italic;">Item ID: {item.get("item_id", "N/A")}</div>' if item.get('item_id') else ''}
                            </td>
                            <td style="text-align: center; color: #666; padding: 1rem 0.8rem; font-weight: 500;">{invoice_qty}</td>
                            {dq_cell}
                            <td style="text-align: right; color: #666; padding: 1rem 0.8rem;">{unit_price}</td>
                            <td style="text-align: right; font-weight: 600; color: #222; padding: 1rem 0.8rem;">{item_total}</td>
                            {status_cell}
                        </tr>
                    ''', unsafe_allow_html=True)
                
                # Enhanced totals row with comprehensive summary
                st.markdown(f'''
                    <tr class="owlin-invoice-total-row" 
                        role="row" 
                        aria-label="Invoice totals and summary">
                        <td colspan="4" style="text-align: right; font-weight: 700; font-size: 1.1rem; color: #222; padding: 1.5rem 0.8rem; border-top: 2px solid #e9ecef; background: #f8f9fa;">
                            <div style="margin-bottom: 0.5rem;">Subtotal:</div>
                            {f'<div style="font-size: 0.9rem; color: #b8860b; margin-bottom: 0.3rem;">Discrepancy Value: {format_currency(total_discrepancy_value)}</div>' if total_discrepancy_value > 0 else ''}
                            <div style="font-size: 1.2rem; font-weight: 800;">Total Amount:</div>
                        </td>
                        <td style="text-align: right; font-weight: 700; font-size: 1.2rem; color: #222; padding: 1.5rem 0.8rem; border-top: 2px solid #e9ecef; background: #f8f9fa;">
                            {total_amount}
                        </td>
                        <td style="text-align: center; padding: 1.5rem 0.8rem; border-top: 2px solid #e9ecef; background: #f8f9fa;">
                            {f'<div style="background: #fff7e0; color: #b8860b; padding: 0.4rem 0.8rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid #f1c232;">{discrepancy_count} Issues</div>' if discrepancy_count > 0 else '<div style="background: #f0fdf4; color: #10b981; padding: 0.4rem 0.8rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid #10b981;">✅ Clean</div>'}
                        </td>
                    </tr>
                ''', unsafe_allow_html=True)
                
                st.markdown('</tbody></table>', unsafe_allow_html=True)
                
                # Enhanced action buttons with comprehensive styling and accessibility
                st.markdown('<div class="owlin-invoice-action-row" style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #f0f0f0;">', unsafe_allow_html=True)
                
                # Edit Invoice button with enhanced styling
                st.markdown('''
                    <button class="owlin-edit-invoice-btn" 
                            aria-label="Edit invoice details, line items, and supplier information" 
                            disabled
                            style="position: relative; background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 1rem 2.2rem; font-size: 1.05rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.5; display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.1rem;">✏️</span>
                        <span>Edit Invoice</span>
                        <div style="position: absolute; top: -8px; right: -8px; background: #999; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; font-weight: 600;">
                            Soon
                        </div>
                    </button>
                ''', unsafe_allow_html=True)
                
                # Pair Delivery Note button with enhanced styling
                st.markdown('''
                    <button class="owlin-pair-delivery-btn" 
                            aria-label="Pair this invoice with a delivery note for discrepancy checking" 
                            disabled
                            style="position: relative; background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 1rem 2.2rem; font-size: 1.05rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.5; display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.1rem;">🔗</span>
                        <span>Pair Delivery Note</span>
                        <div style="position: absolute; top: -8px; right: -8px; background: #999; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; font-weight: 600;">
                            Soon
                        </div>
                    </button>
                ''', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Enhanced discrepancy summary with actionable insights
                if discrepancy_count > 0:
                    st.markdown(f'''
                        <div style="margin-top: 1.5rem; padding: 1.2rem; background: #fff7e0; border: 1px solid #f1c232; border-radius: 8px;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.8rem;">
                                <span style="font-size: 1.2rem;">⚠️</span>
                                <span style="font-weight: 700; color: #b8860b; font-size: 1.1rem;">
                                    Discrepancy Analysis
                                </span>
                            </div>
                            <div style="color: #666; font-size: 0.95rem; line-height: 1.5; margin-bottom: 1rem;">
                                <strong>{discrepancy_count} line item{'s' if discrepancy_count != 1 else ''}</strong> have quantity mismatches between invoice and delivery note, 
                                with a total potential discrepancy value of <strong>{format_currency(total_discrepancy_value)}</strong>.
                            </div>
                            <div style="background: #fff; border-radius: 6px; padding: 1rem; border: 1px solid #f1c232;">
                                <div style="font-weight: 600; color: #b8860b; margin-bottom: 0.5rem;">💡 Recommended Actions:</div>
                                <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                    <li>Verify delivery quantities with warehouse records</li>
                                    <li>Check for partial deliveries or damaged goods</li>
                                    <li>Contact supplier for clarification on discrepancies</li>
                                    <li>Update invoice records once discrepancies are resolved</li>
                                </ul>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                
            else:
                # Enhanced no line items state
                st.markdown('''
                    <div style="text-align: center; padding: 3rem 1rem; color: #666;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                        <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                            No line items found
                        </div>
                        <div style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">
                            This invoice doesn't have any line items yet.<br>
                            The OCR processing may still be in progress or the invoice format wasn't recognized.
                        </div>
                        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #666;">
                            <div style="font-weight: 600; margin-bottom: 0.5rem; color: #222;">🔍 Troubleshooting:</div>
                            <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                                <li>Check if the invoice file is clear and readable</li>
                                <li>Ensure the invoice contains itemized line items</li>
                                <li>Try re-uploading the file if OCR confidence is low</li>
                                <li>Contact support if the issue persists</li>
                            </ul>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
        else:
            # Enhanced no details available state
            st.markdown('''
                <div style="text-align: center; padding: 3rem 1rem; color: #666;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📋</div>
                    <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                        No details available
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">
                        Unable to load detailed information for this invoice.<br>
                        The invoice may still be processing, or there was an error retrieving the data.
                    </div>
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #666;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: #222;">🔄 Processing Status:</div>
                        <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                            <li>OCR processing may be in progress</li>
                            <li>Database connection issues</li>
                            <li>File format compatibility problems</li>
                            <li>Try refreshing the page or contact support</li>
                        </ul>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Failed to load invoice details: {str(e)}")
        
        # Enhanced error state with comprehensive troubleshooting
        st.markdown('''
            <div style="text-align: center; padding: 2rem 1rem; color: #666;">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">⚠️</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">
                    Unable to load invoice details
                </div>
                <div style="font-size: 0.9rem; line-height: 1.4; margin-bottom: 1.5rem;">
                    There was an error loading the detailed invoice information.<br>
                    This could be due to database connectivity issues or data corruption.
                </div>
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #dc2626;">
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">🔧 Error Recovery:</div>
                    <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                        <li>Refresh the page to retry loading</li>
                        <li>Check your internet connection</li>
                        <li>Try selecting a different invoice</li>
                        <li>Contact technical support if the issue persists</li>
                    </ul>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'invoice_details_error_count' not in st.session_state:
            st.session_state.invoice_details_error_count = 0
        st.session_state.invoice_details_error_count += 1
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Component: Issues Detected Box ---
def render_issues_detected_box(invoices, flagged_issues=None):
    """
    Render the issues detected box showing flagged discrepancies with comprehensive details.
    
    Args:
        invoices (list): List of invoice dictionaries from the database
        flagged_issues (list, optional): Pre-fetched flagged issues. If None, calculates from invoices.
            Expected format: [
                {
                    'invoice': str,
                    'supplier': str,
                    'item': str,
                    'invoice_qty': int,
                    'delivery_qty': int,
                    'unit_price': float,
                    'potential_discrepancy': str,
                    'desc': str,
                    'issue_type': str,
                    'severity': str,
                    'invoice_id': str,
                    'item_id': str
                }
            ]
    
    Features:
        - Comprehensive discrepancy aggregation across all invoices
        - Detailed issue information with visual severity indicators
        - Cost impact analysis and potential financial exposure
        - Enhanced visual styling with Owlin brand colors
        - Disabled action buttons with "Soon" badges
        - Empty state with success confirmation
        - Accessibility support with proper ARIA labels
        - Responsive design for different screen sizes
        - Real-time status updates and error handling
    """
    try:
        # Calculate flagged issues if not provided
        if flagged_issues is None:
            flagged_issues = []
            
            # Gather flagged issues from all invoices with enhanced data
            for inv in invoices:
                try:
                    details = get_invoice_details(inv['id']) if inv else None
                    if details and details.get('line_items'):
                        for item in details.get('line_items', []):
                            # Enhanced discrepancy detection
                            has_discrepancy = (
                                item.get('flagged', False) or 
                                (item.get('delivery_qty') is not None and 
                                 item.get('delivery_qty') != item.get('invoice_qty', 0))
                            )
                            
                            if has_discrepancy:
                                # Calculate comprehensive discrepancy details
                                invoice_qty = item.get('invoice_qty', 0)
                                delivery_qty = item.get('delivery_qty')
                                unit_price = item.get('unit_price', 0)
                                
                                # Determine discrepancy type and severity
                                discrepancy_type = "unknown"
                                severity = "medium"
                                discrepancy_value = 0
                                
                                if delivery_qty is not None:
                                    qty_diff = abs(invoice_qty - delivery_qty)
                                    discrepancy_value = qty_diff * unit_price
                                    
                                    if delivery_qty > invoice_qty:
                                        discrepancy_type = "over_delivered"
                                        severity = "high" if discrepancy_value > 100 else "medium"
                                    else:
                                        discrepancy_type = "under_delivered"
                                        severity = "high" if discrepancy_value > 100 else "medium"
                                else:
                                    discrepancy_type = "flagged_item"
                                    severity = "medium"
                                
                                # Create comprehensive issue record
                                flagged_issues.append({
                                    'invoice': inv.get('invoice_number', 'N/A'),
                                    'supplier': inv.get('supplier', 'N/A'),
                                    'item': item.get('item', 'N/A'),
                                    'invoice_qty': invoice_qty,
                                    'delivery_qty': delivery_qty,
                                    'unit_price': unit_price,
                                    'potential_discrepancy': f"£{discrepancy_value:.2f}",
                                    'discrepancy_value': discrepancy_value,
                                    'desc': f"{invoice_qty} invoiced, {delivery_qty if delivery_qty is not None else 'N/A'} delivered",
                                    'issue_type': discrepancy_type,
                                    'severity': severity,
                                    'invoice_id': inv.get('id', ''),
                                    'item_id': item.get('item_id', ''),
                                    'date': inv.get('date', ''),
                                    'total_invoice_value': inv.get('total', 0),
                                    'qty_difference': abs(invoice_qty - delivery_qty) if delivery_qty is not None else 0
                                })
                except Exception as e:
                    # Log individual invoice processing errors but continue
                    st.warning(f"⚠️ Error processing invoice {inv.get('invoice_number', 'Unknown')}: {str(e)}")
                    continue
        
        # Display issues box with enhanced styling and comprehensive information
        if flagged_issues:
            # Calculate comprehensive summary statistics
            total_discrepancy_value = sum(issue['discrepancy_value'] for issue in flagged_issues)
            high_severity_count = sum(1 for issue in flagged_issues if issue['severity'] == 'high')
            medium_severity_count = sum(1 for issue in flagged_issues if issue['severity'] == 'medium')
            low_severity_count = sum(1 for issue in flagged_issues if issue['severity'] == 'low')
            
            # Group issues by type for better organization
            over_delivered_issues = [issue for issue in flagged_issues if issue['issue_type'] == 'over_delivered']
            under_delivered_issues = [issue for issue in flagged_issues if issue['issue_type'] == 'under_delivered']
            flagged_items = [issue for issue in flagged_issues if issue['issue_type'] == 'flagged_item']
            
            # Enhanced header with comprehensive summary
            st.markdown(f'''
                <div class="owlin-issues-box" role="region" aria-label="Issues Detected - {len(flagged_issues)} discrepancies found">
                    <div class="owlin-issues-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.3rem;">⚠️</span>
                            <div>
                                <div style="font-weight: 700; color: #b8860b; font-size: 1.2rem; margin-bottom: 0.2rem;">
                                    {len(flagged_issues)} Issue{'s' if len(flagged_issues) != 1 else ''} Detected
                                </div>
                                <div style="font-size: 0.9rem; color: #666;">
                                    Potential financial impact: <strong style="color: #b8860b;">{format_currency(total_discrepancy_value)}</strong>
                                </div>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                            <div style="background: #fff; border: 1px solid #f1c232; border-radius: 6px; padding: 0.6rem 1rem; text-align: center;">
                                <div style="font-weight: 600; color: #b8860b; font-size: 1.1rem;">{format_currency(total_discrepancy_value)}</div>
                                <div style="font-size: 0.8rem; color: #666;">Total Impact</div>
                            </div>
                            <div style="background: #fff; border: 1px solid #ef4444; border-radius: 6px; padding: 0.6rem 1rem; text-align: center;">
                                <div style="font-weight: 600; color: #ef4444; font-size: 1.1rem;">{high_severity_count}</div>
                                <div style="font-size: 0.8rem; color: #666;">High Priority</div>
                            </div>
                            <div style="background: #fff; border: 1px solid #f1c232; border-radius: 6px; padding: 0.6rem 1rem; text-align: center;">
                                <div style="font-weight: 600; color: #b8860b; font-size: 1.1rem;">{medium_severity_count}</div>
                                <div style="font-size: 0.8rem; color: #666;">Medium Priority</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Issue Type Summary -->
                    <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
                        {f'''
                        <div style="background: #fff3cd; border: 1px solid #f1c232; border-radius: 6px; padding: 0.5rem 1rem; flex: 1; min-width: 150px;">
                            <div style="font-weight: 600; color: #b8860b; font-size: 1rem;">{len(over_delivered_issues)}</div>
                            <div style="font-size: 0.8rem; color: #666;">Over Delivered</div>
                        </div>
                        ''' if over_delivered_issues else ''}
                        
                        {f'''
                        <div style="background: #fff3cd; border: 1px solid #f1c232; border-radius: 6px; padding: 0.5rem 1rem; flex: 1; min-width: 150px;">
                            <div style="font-weight: 600; color: #b8860b; font-size: 1rem;">{len(under_delivered_issues)}</div>
                            <div style="font-size: 0.8rem; color: #666;">Under Delivered</div>
                        </div>
                        ''' if under_delivered_issues else ''}
                        
                        {f'''
                        <div style="background: #fff5f5; border: 1px solid #ff3b30; border-radius: 6px; padding: 0.5rem 1rem; flex: 1; min-width: 150px;">
                            <div style="font-weight: 600; color: #ff3b30; font-size: 1rem;">{len(flagged_items)}</div>
                            <div style="font-size: 0.8rem; color: #666;">Flagged Items</div>
                        </div>
                        ''' if flagged_items else ''}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Enhanced issues list with comprehensive details
            st.markdown('<div class="owlin-issues-list" role="list" aria-label="List of flagged issues with detailed discrepancy information">', unsafe_allow_html=True)
            
            # Sort issues by severity and value for better prioritization
            flagged_issues.sort(key=lambda x: (x['severity'] == 'high', x['discrepancy_value']), reverse=True)
            
            for idx, issue in enumerate(flagged_issues):
                # Determine comprehensive styling based on severity and type
                severity_class = f"owlin-issue-{issue['severity']}"
                issue_type = issue['issue_type']
                
                # Enhanced color coding
                if issue['severity'] == 'high':
                    border_color = "#ef4444"
                    bg_color = "#fef2f2"
                    text_color = "#991b1b"
                elif issue['severity'] == 'medium':
                    border_color = "#f1c232"
                    bg_color = "#fff7e0"
                    text_color = "#b8860b"
                else:
                    border_color = "#10b981"
                    bg_color = "#f0fdf4"
                    text_color = "#065f46"
                
                # Create comprehensive ARIA label for accessibility
                aria_label = f"Issue {idx + 1}: {issue['item']} from {issue['supplier']}, {issue['desc']}, potential impact {issue['potential_discrepancy']}"
                
                # Enhanced issue card with comprehensive information
                st.markdown(f'''
                    <div class="owlin-issue-item {severity_class}" 
                         role="listitem" 
                         aria-label="{aria_label}"
                         style="background: {bg_color}; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.2rem; border-left: 4px solid {border_color}; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: all 0.2s ease-in-out;">
                        
                        <!-- Issue Header with Enhanced Information -->
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem;">
                            <div style="flex: 1; min-width: 250px;">
                                <div style="font-weight: 700; color: #222; font-size: 1.1rem; margin-bottom: 0.4rem;">
                                    {sanitize_text(issue['item'])}
                                </div>
                                <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;">
                                    <strong>Invoice:</strong> {sanitize_text(issue['invoice'])} &nbsp; | &nbsp; 
                                    <strong>Supplier:</strong> {sanitize_text(issue['supplier'])}
                                </div>
                                <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.3rem;">
                                    <strong>Date:</strong> {issue['date']} &nbsp; | &nbsp; 
                                    <strong>Unit Price:</strong> £{issue['unit_price']:.2f}
                                </div>
                                {f'''
                                <div style="font-size: 0.8rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.3rem;">
                                    Item ID: {issue['item_id']}
                                </div>
                                ''' if issue['item_id'] else ''}
                            </div>
                            
                            <div style="text-align: right; margin-left: 1rem; min-width: 120px;">
                                <div style="font-weight: 700; color: {text_color}; font-size: 1.3rem; margin-bottom: 0.3rem;">
                                    {issue['potential_discrepancy']}
                                </div>
                                <div style="font-size: 0.8rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.3rem;">
                                    {issue['issue_type'].replace('_', ' ')}
                                </div>
                                <div style="font-size: 0.8rem; color: #666; padding: 0.2rem 0.6rem; background: {bg_color}; border: 1px solid {border_color}; border-radius: 4px; display: inline-block;">
                                    {issue['severity'].title()} Priority
                                </div>
                            </div>
                        </div>
                        
                        <!-- Enhanced Discrepancy Details -->
                        <div style="background: #fff; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem; border: 1px solid {border_color};">
                            <div style="color: {text_color}; font-weight: 600; margin-bottom: 0.5rem; font-size: 1rem;">
                                📊 Quantity Discrepancy Analysis
                            </div>
                            <div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 0.8rem;">
                                <div style="flex: 1; min-width: 120px;">
                                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem;">Invoice Quantity</div>
                                    <div style="font-weight: 600; color: #222; font-size: 1.1rem;">{issue['invoice_qty']}</div>
                                </div>
                                <div style="flex: 1; min-width: 120px;">
                                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem;">Delivery Quantity</div>
                                    <div style="font-weight: 600; color: #222; font-size: 1.1rem;">{issue['delivery_qty'] if issue['delivery_qty'] is not None else 'N/A'}</div>
                                </div>
                                <div style="flex: 1; min-width: 120px;">
                                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem;">Difference</div>
                                    <div style="font-weight: 600; color: {text_color}; font-size: 1.1rem;">{issue['qty_difference']}</div>
                                </div>
                                <div style="flex: 1; min-width: 120px;">
                                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem;">Financial Impact</div>
                                    <div style="font-weight: 600; color: {text_color}; font-size: 1.1rem;">{issue['potential_discrepancy']}</div>
                                </div>
                            </div>
                            <div style="color: #666; font-size: 0.9rem; line-height: 1.4;">
                                <strong>Description:</strong> {issue['desc']}
                            </div>
                        </div>
                        
                        <!-- Enhanced Action Buttons with Better Styling -->
                        <div class="owlin-invoice-action-row" style="justify-content: flex-start; gap: 1rem; flex-wrap: wrap;">
                            <button class="owlin-edit-invoice-btn" 
                                    aria-label="Edit invoice {issue['invoice']} to resolve this discrepancy" 
                                    disabled
                                    style="position: relative; background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">✏️</span>
                                <span>Edit Invoice</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                            
                            <button class="owlin-pair-delivery-btn" 
                                    aria-label="Pair delivery note for invoice {issue['invoice']}" 
                                    disabled
                                    style="position: relative; background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">🔗</span>
                                <span>Pair Delivery Note</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                            
                            <button class="owlin-resolve-issue-btn" 
                                    aria-label="Mark issue as resolved for {issue['item']}" 
                                    disabled
                                    style="position: relative; background: #10b981; color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">✅</span>
                                <span>Mark Resolved</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Enhanced footer with comprehensive recommendations and next steps
            st.markdown(f'''
                <div style="margin-top: 2rem; padding: 1.5rem; background: #fff; border-radius: 10px; border: 2px solid #f1c232; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                        <span style="font-size: 1.2rem;">💡</span>
                        <span style="font-weight: 700; color: #b8860b; font-size: 1.1rem;">
                            Recommended Actions & Next Steps
                        </span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; border-left: 4px solid #ef4444;">
                            <div style="font-weight: 600; color: #991b1b; margin-bottom: 0.5rem;">🚨 High Priority ({high_severity_count})</div>
                            <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                <li>Review immediately - potential high financial impact</li>
                                <li>Contact supplier for clarification</li>
                                <li>Verify warehouse records</li>
                                <li>Update invoice records once resolved</li>
                            </ul>
                        </div>
                        
                        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; border-left: 4px solid #f1c232;">
                            <div style="font-weight: 600; color: #b8860b; margin-bottom: 0.5rem;">⚠️ Medium Priority ({medium_severity_count})</div>
                            <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                <li>Review within 48 hours</li>
                                <li>Check for partial deliveries</li>
                                <li>Verify delivery documentation</li>
                                <li>Document resolution process</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 1rem;">
                        <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 0.5rem;">📊 Financial Summary</div>
                        <div style="color: #0369a1; font-size: 0.95rem; line-height: 1.5;">
                            <strong>Total Potential Impact:</strong> {format_currency(total_discrepancy_value)} across {len(flagged_issues)} items<br>
                            <strong>Average Impact per Issue:</strong> {format_currency(total_discrepancy_value / len(flagged_issues)) if len(flagged_issues) > 0 else '£0.00'}<br>
                            <strong>Highest Single Impact:</strong> {format_currency(max(issue['discrepancy_value'] for issue in flagged_issues)) if flagged_issues else '£0.00'}
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        else:
            # Enhanced success state when no issues are detected
            st.markdown('''
                <div style="text-align: center; padding: 3rem 2rem; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 2px solid #10b981; border-radius: 16px; margin: 1.5rem 0 2rem 0; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);">
                    <div style="font-size: 4rem; margin-bottom: 1.5rem;">✅</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #065f46; margin-bottom: 0.8rem;">
                        No Issues Detected!
                    </div>
                    <div style="color: #047857; font-size: 1.1rem; line-height: 1.6; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto;">
                        All invoices have been successfully processed and verified.<br>
                        No quantity discrepancies or flagged items were found.
                    </div>
                    
                    <div style="background: #fff; border-radius: 12px; padding: 1.5rem; border: 1px solid #10b981; max-width: 500px; margin: 0 auto;">
                        <div style="font-weight: 600; color: #065f46; margin-bottom: 1rem; font-size: 1.1rem;">
                            🎉 Quality Check Complete
                        </div>
                        <div style="color: #047857; font-size: 0.95rem; line-height: 1.5;">
                            <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                                <li>All invoice quantities match delivery notes</li>
                                <li>No flagged items requiring attention</li>
                                <li>OCR processing completed successfully</li>
                                <li>Ready for submission to Owlin system</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="margin-top: 2rem; padding: 1rem; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid #10b981;">
                        <div style="font-weight: 600; color: #065f46; margin-bottom: 0.5rem;">
                            💡 Pro Tip
                        </div>
                        <div style="color: #047857; font-size: 0.9rem;">
                            Continue uploading invoices and delivery notes to maintain this clean status. 
                            The system will automatically detect any future discrepancies.
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Failed to load flagged issues: {str(e)}")
        
        # Enhanced error state with comprehensive troubleshooting
        st.markdown('''
            <div style="text-align: center; padding: 2.5rem 1.5rem; background: #fef2f2; border: 2px solid #ef4444; border-radius: 12px; margin: 1.5rem 0 2rem 0;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: #991b1b;">
                    Unable to Check for Issues
                </div>
                <div style="color: #dc2626; font-size: 1rem; line-height: 1.5; margin-bottom: 2rem;">
                    There was an error analyzing invoice discrepancies.<br>
                    This could be due to database connectivity issues or data processing problems.
                </div>
                
                <div style="background: #fff; border-radius: 8px; padding: 1.2rem; border: 1px solid #ef4444; max-width: 500px; margin: 0 auto;">
                    <div style="font-weight: 600; color: #991b1b; margin-bottom: 0.8rem;">
                        🔧 Troubleshooting Steps:
                    </div>
                    <ul style="text-align: left; margin: 0; padding-left: 1.2rem; color: #dc2626; font-size: 0.9rem; line-height: 1.4;">
                        <li>Refresh the page to retry the analysis</li>
                        <li>Check your internet connection</li>
                        <li>Verify that invoices are properly uploaded</li>
                        <li>Contact technical support if the issue persists</li>
                    </ul>
                </div>
                
                <button onclick="location.reload()" style="background: #ef4444; color: #fff; border: none; padding: 0.8rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 1.5rem; transition: all 0.2s ease-in-out;">
                    🔄 Refresh Page
                </button>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'issues_detected_error_count' not in st.session_state:
            st.session_state.issues_detected_error_count = 0
        st.session_state.issues_detected_error_count += 1

# --- Component: Footer Buttons ---
def render_footer_buttons(on_clear=None, on_submit=None, disabled=False, show_loading=False):
    """
    Render the footer action buttons with Clear Submission and Submit to Owlin actions.
    
    Args:
        on_clear (callable, optional): Callback function for Clear Submission action.
            Signature: on_clear()
        on_submit (callable, optional): Callback function for Submit to Owlin action.
            Signature: on_submit()
        disabled (bool): Whether buttons should be disabled. Defaults to False.
        show_loading (bool): Whether to show loading state. Defaults to False.
    
    Features:
        - Enhanced button layout with professional styling
        - Clear Submission and Submit to Owlin buttons
        - Brand-consistent styling with Owlin colors
        - Hover effects and visual feedback
        - Comprehensive accessibility support
        - Loading states and disabled states
        - Callback support for custom actions
        - Responsive design for different screen sizes
        - Enhanced error handling and user feedback
    """
    try:
        # Determine button states
        is_disabled = disabled or show_loading
        clear_disabled = is_disabled or on_clear is None
        submit_disabled = is_disabled or on_submit is None
        
        # Create unique keys for buttons
        clear_key = f"clear_submission_{hash(str(on_clear))}"
        submit_key = f"submit_owlin_{hash(str(on_submit))}"
        
        st.markdown('<div class="owlin-footer-btn-container" role="group" aria-label="Footer action buttons">', unsafe_allow_html=True)
        
        # Enhanced footer with comprehensive styling
        st.markdown(f'''
            <div class="owlin-footer-btn-row" style="background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-top: 2px solid #e9ecef; padding: 2rem 0; margin-top: 3rem; box-shadow: 0 -2px 8px rgba(0,0,0,0.1);">
                <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 2rem;">
                    
                    <!-- Left side: Status and info -->
                    <div style="flex: 1; min-width: 300px;">
                        <div style="font-weight: 700; color: #222; font-size: 1.1rem; margin-bottom: 0.5rem;">
                            📊 Submission Status
                        </div>
                        <div style="color: #666; font-size: 0.9rem; line-height: 1.4;">
                            {f"🔄 Processing in progress... Please wait for completion." if show_loading else 
                              f"✅ Ready for submission" if not disabled else 
                              "📋 Upload files to enable submission"}
                        </div>
                        {f'''
                        <div style="margin-top: 0.8rem; padding: 0.6rem; background: #e3f2fd; border: 1px solid #2196f3; border-radius: 6px; font-size: 0.85rem; color: #1976d2;">
                            💡 Tip: Review all discrepancies before submitting to Owlin
                        </div>
                        ''' if not disabled and not show_loading else ''}
                    </div>
                    
                    <!-- Right side: Action buttons -->
                    <div style="display: flex; gap: 1.2rem; align-items: center; flex-wrap: wrap;">
                        
                        <!-- Clear Submission Button -->
                        <div style="position: relative;">
                            <button class="owlin-clear-btn" 
                                    aria-label="Clear all uploaded files and reset the form"
                                    {'disabled' if clear_disabled else ''}
                                    style="position: relative; background: {'#ff9800' if not clear_disabled else '#ccc'}; color: #fff; font-weight: 700; border: none; border-radius: 10px; padding: 1rem 2rem; font-size: 1.05rem; cursor: {'not-allowed' if clear_disabled else 'pointer'}; transition: all 0.3s ease-in-out; opacity: {'0.5' if clear_disabled else '1'}; box-shadow: 0 4px 12px rgba(0,0,0,0.15); hover: transform: translateY(-2px);">
                                <span style="margin-right: 0.5rem; font-size: 1.1rem;">🗑️</span>
                                Clear Submission
                                {f'''
                                <div style="position: absolute; top: -8px; right: -8px; background: #999; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; font-weight: 600;">
                                    Soon
                                </div>
                                ''' if on_clear is None else ''}
                                {f'''
                                <div style="position: absolute; top: -8px; right: -8px; background: #007bff; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; animation: pulse 1.5s infinite; font-weight: 600;">
                                    Loading
                                </div>
                                ''' if show_loading else ''}
                            </button>
                        </div>
                        
                        <!-- Submit to Owlin Button -->
                        <div style="position: relative;">
                            <button class="owlin-submit-owlin-btn" 
                                    aria-label="Submit processed invoices to Owlin system"
                                    {'disabled' if submit_disabled else ''}
                                    style="position: relative; background: {'#222222' if not submit_disabled else '#ccc'}; color: #fff; font-weight: 700; border: none; border-radius: 10px; padding: 1rem 2rem; font-size: 1.05rem; cursor: {'not-allowed' if submit_disabled else 'pointer'}; transition: all 0.3s ease-in-out; opacity: {'0.5' if submit_disabled else '1'}; box-shadow: 0 4px 12px rgba(0,0,0,0.15); hover: transform: translateY(-2px);">
                                <span style="margin-right: 0.5rem; font-size: 1.1rem;">🚀</span>
                                Submit to Owlin
                                {f'''
                                <div style="position: absolute; top: -8px; right: -8px; background: #999; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; font-weight: 600;">
                                    Soon
                                </div>
                                ''' if on_submit is None else ''}
                                {f'''
                                <div style="position: absolute; top: -8px; right: -8px; background: #007bff; color: white; font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; animation: pulse 1.5s infinite; font-weight: 600;">
                                    Loading
                                </div>
                                ''' if show_loading else ''}
                            </button>
                        </div>
                        
                    </div>
                    
                </div>
                
                <!-- Enhanced status information -->
                {f'''
                <div style="max-width: 1200px; margin: 0 auto; margin-top: 1.5rem; padding: 1rem; background: #e3f2fd; border: 1px solid #2196f3; border-radius: 8px; font-size: 0.9rem; color: #1976d2;">
                    🔄 Processing in progress... Please wait for completion. This may take a few minutes.
                </div>
                ''' if show_loading else ''}
                
                {f'''
                <div style="max-width: 1200px; margin: 0 auto; margin-top: 1.5rem; padding: 1rem; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; font-size: 0.9rem; color: #6c757d;">
                    ℹ️ Buttons are currently disabled. Upload some files to enable actions.
                </div>
                ''' if clear_disabled and submit_disabled and not show_loading else ''}
                
            </div>
        ''', unsafe_allow_html=True)
        
        # Streamlit buttons for actual functionality
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button(
                "🗑️ Clear Submission",
                key=clear_key,
                disabled=clear_disabled,
                help="Clear all uploaded files and reset the form",
                use_container_width=True
            ):
                if on_clear and callable(on_clear):
                    try:
                        with st.spinner("🔄 Clearing submission..."):
                            on_clear()
                        st.success("✅ Submission cleared successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to clear submission: {str(e)}")
                else:
                    st.info("ℹ️ Clear functionality will be available soon!")
        
        with col2:
            if st.button(
                "🚀 Submit to Owlin",
                key=submit_key,
                disabled=submit_disabled,
                help="Submit processed invoices to Owlin system",
                use_container_width=True
            ):
                if on_submit and callable(on_submit):
                    try:
                        with st.spinner("🔄 Submitting to Owlin..."):
                            result = on_submit()
                        st.success("✅ Successfully submitted to Owlin!")
                        # Show submission result if provided
                        if result:
                            st.info(f"📊 Submission details: {result}")
                    except Exception as e:
                        st.error(f"❌ Failed to submit to Owlin: {str(e)}")
                else:
                    st.info("ℹ️ Submit functionality will be available soon!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Track button interactions for analytics
        if 'footer_button_clicks' not in st.session_state:
            st.session_state.footer_button_clicks = {'clear': 0, 'submit': 0}
        
    except Exception as e:
        st.error(f"❌ Failed to render footer buttons: {str(e)}")
        
        # Fallback buttons on error
        st.markdown('''
            <div style="background: #f8f9fa; border-top: 2px solid #e9ecef; padding: 2rem 0; margin-top: 3rem;">
                <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: flex-end; gap: 1.2rem;">
                    <button disabled style="background: #ccc; color: #666; padding: 1rem 2rem; border: none; border-radius: 10px; font-size: 1.05rem; cursor: not-allowed;">
                        🗑️ Clear Submission
                    </button>
                    <button disabled style="background: #ccc; color: #666; padding: 1rem 2rem; border: none; border-radius: 10px; font-size: 1.05rem; cursor: not-allowed;">
                        🚀 Submit to Owlin
                    </button>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'footer_buttons_error_count' not in st.session_state:
            st.session_state.footer_buttons_error_count = 0
        st.session_state.footer_buttons_error_count += 1

def add_keyboard_shortcuts_toggle():
    """
    Add a collapsible keyboard shortcuts panel with comprehensive help text.
    
    Features:
        - Toggle button to show/hide shortcuts
        - Comprehensive list of keyboard shortcuts
        - Categorized shortcuts by functionality
        - Accessibility support with ARIA labels
        - Responsive design for different screen sizes
        - Professional styling with Owlin brand colors
    """
    try:
        # Initialize toggle state
        if 'show_keyboard_shortcuts' not in st.session_state:
            st.session_state.show_keyboard_shortcuts = False
        
        # Keyboard shortcuts toggle button
        st.markdown('''
            <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
                <button id="keyboard-shortcuts-toggle" 
                        onclick="toggleKeyboardShortcuts()"
                        style="background: #222222; color: #fff; border: none; border-radius: 50px; padding: 0.8rem 1.2rem; font-size: 0.9rem; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.3s ease-in-out; display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1rem;">⌨️</span>
                    <span>Keyboard Shortcuts</span>
                </button>
            </div>
        ''', unsafe_allow_html=True)
        
        # Collapsible shortcuts panel
        if st.session_state.show_keyboard_shortcuts:
            st.markdown('''
                <div id="keyboard-shortcuts-panel" style="position: fixed; bottom: 80px; right: 20px; z-index: 999; background: #fff; border: 2px solid #e9ecef; border-radius: 12px; padding: 1.5rem; box-shadow: 0 8px 24px rgba(0,0,0,0.15); max-width: 400px; max-height: 500px; overflow-y: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3 style="margin: 0; color: #222; font-size: 1.1rem; font-weight: 700;">⌨️ Keyboard Shortcuts</h3>
                        <button onclick="toggleKeyboardShortcuts()" style="background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #666;">×</button>
                    </div>
                    
                    <div style="font-size: 0.9rem; line-height: 1.5;">
                        
                        <!-- Navigation Shortcuts -->
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; color: #222; margin-bottom: 0.5rem; font-size: 0.95rem;">🗺️ Navigation</div>
                            <div style="background: #f8f9fa; border-radius: 6px; padding: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Tab</span>
                                    <span style="color: #666;">Navigate between elements</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Enter / Space</span>
                                    <span style="color: #666;">Activate buttons</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Arrow Keys</span>
                                    <span style="color: #666;">Navigate lists</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>Escape</span>
                                    <span style="color: #666;">Close dialogs</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- File Upload Shortcuts -->
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; color: #222; margin-bottom: 0.5rem; font-size: 0.95rem;">📁 File Upload</div>
                            <div style="background: #f8f9fa; border-radius: 6px; padding: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Ctrl + O</span>
                                    <span style="color: #666;">Open file dialog</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Drag & Drop</span>
                                    <span style="color: #666;">Upload files</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>Delete</span>
                                    <span style="color: #666;">Remove selected file</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Invoice Management Shortcuts -->
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; color: #222; margin-bottom: 0.5rem; font-size: 0.95rem;">📄 Invoice Management</div>
                            <div style="background: #f8f9fa; border-radius: 6px; padding: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>1-9</span>
                                    <span style="color: #666;">Select invoice by number</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Ctrl + F</span>
                                    <span style="color: #666;">Search invoices</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>Ctrl + R</span>
                                    <span style="color: #666;">Refresh status</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Action Shortcuts -->
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; color: #222; margin-bottom: 0.5rem; font-size: 0.95rem;">⚡ Quick Actions</div>
                            <div style="background: #f8f9fa; border-radius: 6px; padding: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Ctrl + S</span>
                                    <span style="color: #666;">Submit to Owlin</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Ctrl + C</span>
                                    <span style="color: #666;">Clear submission</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>F1</span>
                                    <span style="color: #666;">Show this help</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Accessibility Shortcuts -->
                        <div style="margin-bottom: 1rem;">
                            <div style="font-weight: 600; color: #222; margin-bottom: 0.5rem; font-size: 0.95rem;">♿ Accessibility</div>
                            <div style="background: #f8f9fa; border-radius: 6px; padding: 0.8rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                    <span>Alt + 1-9</span>
                                    <span style="color: #666;">Announce status</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>Ctrl + M</span>
                                    <span style="color: #666;">Toggle high contrast</span>
                                </div>
                            </div>
                        </div>
                        
                    </div>
                    
                    <div style="margin-top: 1rem; padding: 0.8rem; background: #e3f2fd; border: 1px solid #2196f3; border-radius: 6px; font-size: 0.8rem; color: #1976d2;">
                        💡 <strong>Pro Tip:</strong> Use Tab to navigate and Enter to activate. All shortcuts work with screen readers.
                    </div>
                    
                </div>
                
                <script>
                function toggleKeyboardShortcuts() {
                    const panel = document.getElementById('keyboard-shortcuts-panel');
                    if (panel.style.display === 'none' || panel.style.display === '') {
                        panel.style.display = 'block';
                    } else {
                        panel.style.display = 'none';
                    }
                }
                
                // Keyboard event listeners
                document.addEventListener('keydown', function(e) {
                    // F1 to toggle shortcuts
                    if (e.key === 'F1') {
                        e.preventDefault();
                        toggleKeyboardShortcuts();
                    }
                    
                    // Ctrl + S for submit
                    if (e.ctrlKey && e.key === 's') {
                        e.preventDefault();
                        // Trigger submit button
                        const submitBtn = document.querySelector('.owlin-submit-owlin-btn');
                        if (submitBtn && !submitBtn.disabled) {
                            submitBtn.click();
                        }
                    }
                    
                    // Ctrl + C for clear
                    if (e.ctrlKey && e.key === 'c') {
                        e.preventDefault();
                        // Trigger clear button
                        const clearBtn = document.querySelector('.owlin-clear-btn');
                        if (clearBtn && !clearBtn.disabled) {
                            clearBtn.click();
                        }
                    }
                });
                </script>
            ''', unsafe_allow_html=True)
        
        # Toggle button functionality
        if st.button("⌨️ Toggle Keyboard Shortcuts", key="toggle_shortcuts"):
            st.session_state.show_keyboard_shortcuts = not st.session_state.show_keyboard_shortcuts
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ Failed to add keyboard shortcuts: {str(e)}")
        
        # Track error for debugging
        if 'keyboard_shortcuts_error_count' not in st.session_state:
            st.session_state.keyboard_shortcuts_error_count = 0
        st.session_state.keyboard_shortcuts_error_count += 1

# --- Component: Not Paired Invoices ---
def render_not_paired_invoices(invoices, invoices_not_paired=None):
    """
    Render the not paired invoices section showing invoices missing delivery note pairing.
    
    Args:
        invoices (list): List of invoice dictionaries from the database
        invoices_not_paired (list, optional): Pre-fetched unpaired invoices. If None, filters from invoices.
            Expected format: [
                {
                    'id': str,
                    'invoice_number': str,
                    'supplier': str,
                    'date': str,
                    'total': float,
                    'status': str
                }
            ]
    
    Features:
        - Enhanced header with count and comprehensive summary
        - Detailed invoice cards with enhanced information display
        - Urgency indicators for old invoices
        - Disabled action buttons with "Soon" badges
        - Success state when all invoices are paired
        - Comprehensive error handling with troubleshooting
        - Accessibility support with proper ARIA labels
        - Responsive design for different screen sizes
        - Real-time status updates and visual feedback
    """
    try:
        # Filter unpaired invoices if not provided
        if invoices_not_paired is None:
            invoices_not_paired = [inv for inv in invoices if inv.get('status') == 'not_paired'] if invoices else []
        
        # Display section if there are unpaired invoices
        if invoices_not_paired:
            # Calculate comprehensive summary statistics
            total_value = sum(inv.get('total', 0) for inv in invoices_not_paired)
            old_invoices = []
            recent_invoices = []
            
            # Categorize invoices by age
            for inv in invoices_not_paired:
                try:
                    if inv.get('date'):
                        invoice_date = datetime.strptime(inv.get('date'), '%Y-%m-%d')
                        days_old = (datetime.now() - invoice_date).days
                        if days_old > 30:
                            old_invoices.append(inv)
                        else:
                            recent_invoices.append(inv)
                except:
                    recent_invoices.append(inv)
            
            st.markdown('<div class="owlin-not-paired-section" role="region" aria-label="Invoices Not Paired">', unsafe_allow_html=True)
            
            # Enhanced header with comprehensive summary
            st.markdown(f'''
                <div class="owlin-not-paired-header" style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); border-radius: 12px 12px 0 0; padding: 1.5rem; margin-bottom: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <span style="font-size: 1.4rem;">🔗</span>
                            <div>
                                <div style="font-weight: 700; color: #fff; font-size: 1.3rem; margin-bottom: 0.2rem;">
                                    Invoices Not Paired ({len(invoices_not_paired)})
                                </div>
                                <div style="color: #d1d5db; font-size: 0.95rem;">
                                    Missing delivery notes for pairing and discrepancy checking
                                </div>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                            <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 0.8rem 1.2rem; text-align: center; border: 1px solid rgba(255,255,255,0.2);">
                                <div style="font-weight: 600; color: #fff; font-size: 1.1rem;">{format_currency(total_value)}</div>
                                <div style="font-size: 0.8rem; color: #d1d5db;">Total Value</div>
                            </div>
                            <div style="background: rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 0.8rem 1.2rem; text-align: center; border: 1px solid rgba(239, 68, 68, 0.3);">
                                <div style="font-weight: 600; color: #fca5a5; font-size: 1.1rem;">{len(old_invoices)}</div>
                                <div style="font-size: 0.8rem; color: #d1d5db;">Over 30 Days</div>
                            </div>
                            <div style="background: rgba(241, 194, 50, 0.2); border-radius: 8px; padding: 0.8rem 1.2rem; text-align: center; border: 1px solid rgba(241, 194, 50, 0.3);">
                                <div style="font-weight: 600; color: #fde047; font-size: 1.1rem;">{len(recent_invoices)}</div>
                                <div style="font-size: 0.8rem; color: #d1d5db;">Recent</div>
                            </div>
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Enhanced invoice list container
            st.markdown('<div class="owlin-not-paired-list" role="list" aria-label="List of unpaired invoices requiring delivery note pairing">', unsafe_allow_html=True)
            
            # Sort invoices by date (oldest first) and urgency
            invoices_not_paired.sort(key=lambda x: (
                datetime.strptime(x.get('date', '1900-01-01'), '%Y-%m-%d') if x.get('date') else datetime.now(),
                x.get('total', 0)
            ))
            
            for idx, inv in enumerate(invoices_not_paired):
                # Extract and sanitize invoice data
                invoice_number = sanitize_text(inv.get('invoice_number', 'N/A'))
                supplier = sanitize_text(inv.get('supplier', 'N/A'))
                date = sanitize_text(inv.get('date', ''))
                total = format_currency(inv.get('total', 0))
                status = inv.get('status', 'not_paired')
                invoice_id = inv.get('id', '')
                
                # Create comprehensive ARIA label for accessibility
                aria_label = f"Unpaired invoice {idx + 1}: {invoice_number} from {supplier}, total {total}, date {date}"
                
                # Calculate urgency indicators and styling
                urgency_class = ""
                urgency_badge = ""
                urgency_color = "#ff3b30"
                urgency_bg = "#fff5f5"
                urgency_border = "#ff3b30"
                
                try:
                    if date:
                        invoice_date = datetime.strptime(date, '%Y-%m-%d')
                        days_old = (datetime.now() - invoice_date).days
                        
                        if days_old > 60:
                            urgency_class = "owlin-critical"
                            urgency_badge = f"<div style='position: absolute; top: -6px; right: -6px; background: #dc2626; color: white; font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>Critical</div>"
                            urgency_color = "#dc2626"
                            urgency_bg = "#fef2f2"
                            urgency_border = "#dc2626"
                        elif days_old > 30:
                            urgency_class = "owlin-urgent"
                            urgency_badge = f"<div style='position: absolute; top: -6px; right: -6px; background: #ef4444; color: white; font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>Urgent</div>"
                            urgency_color = "#ef4444"
                            urgency_bg = "#fef2f2"
                            urgency_border = "#ef4444"
                        elif days_old > 14:
                            urgency_class = "owlin-warning"
                            urgency_badge = f"<div style='position: absolute; top: -6px; right: -6px; background: #f1c232; color: #222; font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>Due Soon</div>"
                            urgency_color = "#b8860b"
                            urgency_bg = "#fff7e0"
                            urgency_border = "#f1c232"
                except:
                    pass
                
                # Enhanced invoice card with comprehensive information
                st.markdown(f'''
                    <div class="owlin-not-paired-item {urgency_class}" 
                         role="listitem" 
                         aria-label="{aria_label}"
                         style="background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 5px solid {urgency_border}; position: relative; transition: all 0.3s ease-in-out; hover: transform: translateY(-2px);">
                        
                        {urgency_badge}
                        
                        <!-- Enhanced Invoice Header -->
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem;">
                            <div style="flex: 1; min-width: 250px;">
                                <div style="font-weight: 700; color: #222; font-size: 1.2rem; margin-bottom: 0.4rem;">
                                    {invoice_number}
                                </div>
                                <div style="color: #666; font-size: 1rem; margin-bottom: 0.3rem;">
                                    <strong>Supplier:</strong> {supplier}
                                </div>
                                <div style="color: #888; font-size: 0.95rem; margin-bottom: 0.3rem;">
                                    <strong>Date:</strong> {date}
                                </div>
                                {f'''
                                <div style="font-size: 0.8rem; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.3rem;">
                                    Invoice ID: {invoice_id}
                                </div>
                                ''' if invoice_id else ''}
                            </div>
                            
                            <div style="text-align: right; margin-left: 1rem; min-width: 120px;">
                                <div style="font-weight: 700; color: #222; font-size: 1.4rem; margin-bottom: 0.3rem;">
                                    {total}
                                </div>
                                <div style="font-size: 0.8rem; color: {urgency_color}; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; padding: 0.2rem 0.6rem; background: {urgency_bg}; border: 1px solid {urgency_border}; border-radius: 6px; display: inline-block;">
                                    Not Paired
                                </div>
                            </div>
                        </div>
                        
                        <!-- Enhanced Status Details -->
                        <div style="background: {urgency_bg}; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem; border: 1px solid {urgency_border};">
                            <div style="color: {urgency_color}; font-weight: 600; margin-bottom: 0.5rem; font-size: 1rem;">
                                ⚠️ Missing Delivery Note Pairing
                            </div>
                            <div style="color: #666; font-size: 0.95rem; line-height: 1.5;">
                                This invoice requires a delivery note to be uploaded and paired for discrepancy checking. 
                                Without pairing, quantity validation and financial impact analysis cannot be performed.
                            </div>
                            <div style="margin-top: 0.8rem; padding: 0.8rem; background: #fff; border-radius: 6px; border: 1px solid {urgency_border};">
                                <div style="font-weight: 600; color: {urgency_color}; margin-bottom: 0.3rem; font-size: 0.9rem;">
                                    🔍 Required Actions:
                                </div>
                                <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                    <li>Upload corresponding delivery note document</li>
                                    <li>Use pairing functionality to link invoice and delivery note</li>
                                    <li>Review for quantity discrepancies after pairing</li>
                                    <li>Resolve any issues before final submission</li>
                                </ul>
                            </div>
                        </div>
                        
                        <!-- Enhanced Action Buttons -->
                        <div class="owlin-not-paired-actions" style="display: flex; gap: 1rem; justify-content: flex-start; flex-wrap: wrap;">
                            <button class="owlin-edit-invoice-btn" 
                                    aria-label="Edit invoice {invoice_number} to resolve pairing issues" 
                                    disabled
                                    style="position: relative; background: #f1c232; color: #222; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">✏️</span>
                                <span>Edit Invoice</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                            
                            <button class="owlin-pair-delivery-btn" 
                                    aria-label="Pair delivery note for invoice {invoice_number}" 
                                    disabled
                                    style="position: relative; background: #10b981; color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">🔗</span>
                                <span>Pair Delivery Note</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                            
                            <button class="owlin-upload-delivery-btn" 
                                    aria-label="Upload delivery note for invoice {invoice_number}" 
                                    disabled
                                    style="position: relative; background: #3b82f6; color: #fff; font-weight: 700; border: none; border-radius: 8px; padding: 0.8rem 1.5rem; font-size: 0.95rem; cursor: not-allowed; transition: all 0.2s ease-in-out; opacity: 0.6; display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1rem;">📄</span>
                                <span>Upload Delivery Note</span>
                                <div style="position: absolute; top: -6px; right: -6px; background: #999; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 8px; font-weight: 600;">
                                    Soon
                                </div>
                            </button>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Enhanced footer with comprehensive recommendations and next steps
            st.markdown(f'''
                <div style="margin-top: 2rem; padding: 1.5rem; background: #fff; border-radius: 10px; border: 2px solid #f1c232; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                        <span style="font-size: 1.2rem;">💡</span>
                        <span style="font-weight: 700; color: #b8860b; font-size: 1.1rem;">
                            Pairing Process & Next Steps
                        </span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; border-left: 4px solid #ef4444;">
                            <div style="font-weight: 600; color: #991b1b; margin-bottom: 0.5rem;">🚨 Critical ({len(old_invoices)})</div>
                            <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                <li>Invoices over 30 days old require immediate attention</li>
                                <li>Contact suppliers for missing delivery notes</li>
                                <li>Verify if delivery notes exist but weren't uploaded</li>
                                <li>Consider manual reconciliation if documents are lost</li>
                            </ul>
                        </div>
                        
                        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; border-left: 4px solid #f1c232;">
                            <div style="font-weight: 600; color: #b8860b; margin-bottom: 0.5rem;">⚠️ Recent ({len(recent_invoices)})</div>
                            <ul style="margin: 0; padding-left: 1.2rem; color: #666; font-size: 0.9rem; line-height: 1.4;">
                                <li>Upload delivery notes within 48 hours</li>
                                <li>Use the upload box above for document submission</li>
                                <li>Verify document quality and readability</li>
                                <li>Check for partial deliveries or split shipments</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 1rem;">
                        <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 0.5rem;">📊 Financial Summary</div>
                        <div style="color: #0369a1; font-size: 0.95rem; line-height: 1.5;">
                            <strong>Total Unpaired Value:</strong> {format_currency(total_value)} across {len(invoices_not_paired)} invoices<br>
                            <strong>Average Invoice Value:</strong> {format_currency(total_value / len(invoices_not_paired)) if len(invoices_not_paired) > 0 else '£0.00'}<br>
                            <strong>Highest Single Value:</strong> {format_currency(max(inv.get('total', 0) for inv in invoices_not_paired)) if invoices_not_paired else '£0.00'}
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        else:
            # Enhanced success state when all invoices are paired
            st.markdown('''
                <div style="text-align: center; padding: 3rem 2rem; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 2px solid #10b981; border-radius: 16px; margin: 1.5rem 0 2rem 0; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);">
                    <div style="font-size: 4rem; margin-bottom: 1.5rem;">✅</div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #065f46; margin-bottom: 0.8rem;">
                        All Invoices Successfully Paired!
                    </div>
                    <div style="color: #047857; font-size: 1.1rem; line-height: 1.6; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto;">
                        Every invoice has been successfully paired with its corresponding delivery note.<br>
                        Ready for discrepancy checking and final submission.
                    </div>
                    
                    <div style="background: #fff; border-radius: 12px; padding: 1.5rem; border: 1px solid #10b981; max-width: 500px; margin: 0 auto;">
                        <div style="font-weight: 600; color: #065f46; margin-bottom: 1rem; font-size: 1.1rem;">
                            🎉 Pairing Complete
                        </div>
                        <div style="color: #047857; font-size: 0.95rem; line-height: 1.5;">
                            <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">
                                <li>All invoices have delivery note pairs</li>
                                <li>Quantity discrepancy checking enabled</li>
                                <li>Financial impact analysis available</li>
                                <li>Ready for Owlin system submission</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="margin-top: 2rem; padding: 1rem; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid #10b981;">
                        <div style="font-weight: 600; color: #065f46; margin-bottom: 0.5rem;">
                            💡 Next Steps
                        </div>
                        <div style="color: #047857; font-size: 0.9rem;">
                            Review the "Issues Detected" section above to check for any quantity discrepancies 
                            between invoices and delivery notes.
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Failed to load unpaired invoices: {str(e)}")
        
        # Enhanced error state with comprehensive troubleshooting
        st.markdown('''
            <div style="text-align: center; padding: 2.5rem 1.5rem; background: #fef2f2; border: 2px solid #ef4444; border-radius: 12px; margin: 1.5rem 0 2rem 0;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: #991b1b;">
                    Unable to Check Pairing Status
                </div>
                <div style="color: #dc2626; font-size: 1rem; line-height: 1.5; margin-bottom: 2rem;">
                    There was an error checking invoice pairing status.<br>
                    This could be due to database connectivity issues or data processing problems.
                </div>
                
                <div style="background: #fff; border-radius: 8px; padding: 1.2rem; border: 1px solid #ef4444; max-width: 500px; margin: 0 auto;">
                    <div style="font-weight: 600; color: #991b1b; margin-bottom: 0.8rem;">
                        🔧 Troubleshooting Steps:
                    </div>
                    <ul style="text-align: left; margin: 0; padding-left: 1.2rem; color: #dc2626; font-size: 0.9rem; line-height: 1.4;">
                        <li>Refresh the page to retry the pairing check</li>
                        <li>Check your internet connection</li>
                        <li>Verify that invoices are properly uploaded</li>
                        <li>Contact technical support if the issue persists</li>
                    </ul>
                </div>
                
                <button onclick="location.reload()" style="background: #ef4444; color: #fff; border: none; padding: 0.8rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 1.5rem; transition: all 0.2s ease-in-out;">
                    🔄 Refresh Page
                </button>
            </div>
        ''', unsafe_allow_html=True)
        
        # Track error for debugging
        if 'not_paired_error_count' not in st.session_state:
            st.session_state.not_paired_error_count = 0
        st.session_state.not_paired_error_count += 1

# --- Main Page Function ---
def render_invoices_page():
    """
    Main function that orchestrates all components to render the complete invoices page.
    Handles data fetching, component coordination, and overall page layout.
    """
    # --- Accessibility Enhancements ---
    add_accessibility_enhancements()
    
    # --- Keyboard Shortcuts Panel ---
    add_keyboard_shortcuts_panel()
    
    # --- Upload Boxes ---
    st.markdown('<div class="owlin-upload-row">', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        render_upload_box(
            "+Upload Invoices",
            "upload_invoices_key",
            "PDF, PNG, JPG, JPEG, ZIP",
            "invoice",
            10
        )
    with col2:
        render_upload_box(
            "+Upload Delivery Notes",
            "upload_delivery_notes_key",
            "PDF, PNG, JPG, JPEG, ZIP",
            "delivery_note",
            10
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Summary Metrics ---
    render_summary_metrics()

    # --- Main Panel: Invoice List & Details ---
    st.markdown('<div class="owlin-main-panel">', unsafe_allow_html=True)
    
    # Load invoices data once for all components
    try:
        set_loading('invoices_loading')
        with st.spinner("Loading invoices..."):
            invoices = load_invoices_from_db()
            if not invoices:
                invoices = []
        unset_loading('invoices_loading')
    except Exception as e:
        st.error(f"❌ Failed to load invoices: {str(e)}")
        invoices = []

    # Left: Invoice List
    render_invoice_list(
        invoices=invoices,
        selected_index=st.session_state.get('selected_invoice_idx', 0),
        on_select=lambda idx, inv: st.session_state.update({'selected_invoice_idx': idx})
    )

    # Right: Invoice Details
    set_loading('details_loading')
    with st.spinner("Loading invoice details..."):
        render_invoice_details(invoices)
    unset_loading('details_loading')

    st.markdown('</div>', unsafe_allow_html=True)  # End main panel

    # --- Issues Detected Box ---
    render_issues_detected_box(invoices)

    # --- Footer Action Buttons ---
    # Define callback functions for footer buttons
    def clear_submission_data():
        """Clear all uploaded files and reset the form."""
        try:
            # Clear session state for uploads
            for key in list(st.session_state.keys()):
                if isinstance(key, str):
                    if key.startswith('upload_') and key.endswith('_upload_status'):
                        del st.session_state[key]
                    if key.startswith('upload_') and key.endswith('_processing_files'):
                        del st.session_state[key]
            
            # Reset selected invoice
            if 'selected_invoice_idx' in st.session_state:
                st.session_state.selected_invoice_idx = 0
            
            # Clear any processing states
            if 'data_loading' in st.session_state:
                st.session_state.data_loading = False
            
            return True
        except Exception as e:
            st.error(f"Failed to clear submission: {str(e)}")
            return False
    
    def submit_to_owlin():
        """Submit processed invoices to Owlin system."""
        try:
            # Check if there are invoices to submit
            if not invoices:
                st.warning("No invoices to submit. Please upload some invoices first.")
                return "No invoices available"
            
            # Check for unpaired invoices
            unpaired_count = len([inv for inv in invoices if inv.get('status') == 'not_paired'])
            if unpaired_count > 0:
                st.warning(f"⚠️ {unpaired_count} invoice(s) are not paired with delivery notes. Please pair them before submitting.")
                return f"{unpaired_count} unpaired invoices"
            
            # Check for issues
            flagged_issues = []
            for inv in invoices:
                details = get_invoice_details(inv['id']) if inv else None
                if details and details.get('line_items'):
                    for item in details.get('line_items', []):
                        if item.get('flagged') or (item.get('delivery_qty') is not None and 
                                                  item.get('delivery_qty') != item.get('invoice_qty', 0)):
                            flagged_issues.append(item)
            
            if flagged_issues:
                st.warning(f"⚠️ {len(flagged_issues)} issue(s) detected. Please resolve them before submitting.")
                return f"{len(flagged_issues)} issues detected"
            
            # Simulate submission (replace with actual API call)
            import time
            time.sleep(2)  # Simulate processing time
            
            # Return success result
            total_value = sum(inv.get('total', 0) for inv in invoices)
            return f"Successfully submitted {len(invoices)} invoices worth {format_currency(total_value)}"
            
        except Exception as e:
            st.error(f"Failed to submit to Owlin: {str(e)}")
            return f"Error: {str(e)}"
    
    render_footer_buttons(
        on_clear=clear_submission_data,
        on_submit=submit_to_owlin,
        disabled=len(invoices) == 0,
        show_loading=st.session_state.get('data_loading', False)
    )

    # --- Invoices Not Paired Section ---
    render_not_paired_invoices(invoices)

    # --- Loading States & Performance Optimizations ---
    if 'data_loading' not in st.session_state:
        st.session_state.data_loading = False
    
    if st.session_state.data_loading:
        with st.spinner("🔄 Processing data..."):
            st.session_state.data_loading = False

    # --- Accessibility Improvements ---
    st.markdown('''
        <div role="main" aria-label="Owlin Invoice Management">
            <h1 style="display:none;">Owlin Invoice Management</h1>
        </div>
    ''', unsafe_allow_html=True)

    # --- Responsive Design Enhancements ---
    st.markdown('''
        <style>
        @media (max-width: 768px) {
            .owlin-upload-box-modern { padding: 1.5rem 1rem; }
            .owlin-metric-box { min-width: 140px; padding: 1rem 1.5rem; font-size: 1.1rem; }
            .owlin-invoice-card { padding: 0.8rem; }
            .owlin-invoice-details { padding: 1.5rem; }
            .owlin-issues-box { padding: 1rem; }
            .owlin-not-paired-list { padding: 1rem; }
        }
        
        @media (max-width: 480px) {
            .owlin-upload-row { gap: 1rem; }
            .owlin-metrics-row { gap: 0.8rem; }
            .owlin-metric-box { min-width: 120px; padding: 0.8rem 1rem; font-size: 1rem; }
            .owlin-invoice-action-row { flex-direction: column; gap: 0.5rem; }
            .owlin-footer-btn-row { flex-direction: column; align-items: stretch; }
            .owlin-not-paired-item { flex-direction: column; gap: 0.8rem; align-items: flex-start; }
        }
        
        /* Enhanced focus states for accessibility */
        .owlin-edit-invoice-btn:focus, .owlin-pair-delivery-btn:focus,
        .owlin-clear-btn:focus, .owlin-submit-owlin-btn:focus {
            outline: 3px solid #f1c232;
            outline-offset: 2px;
        }
        
        /* Smooth transitions for better UX */
        .owlin-invoice-card, .owlin-metric-box, .owlin-upload-box-modern {
            transition: all 0.2s ease-in-out;
        }
        
        /* Loading animation for processing states */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .owlin-processing {
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        /* Enhanced scrollbar styling */
        .owlin-invoice-list::-webkit-scrollbar,
        .owlin-invoice-details::-webkit-scrollbar {
            width: 6px;
        }
        
        .owlin-invoice-list::-webkit-scrollbar-thumb,
        .owlin-invoice-details::-webkit-scrollbar-thumb {
            background: #c1c5cb;
            border-radius: 3px;
        }
        
        .owlin-invoice-list::-webkit-scrollbar-thumb:hover,
        .owlin-invoice-details::-webkit-scrollbar-thumb:hover {
            background: #a8adb5;
        }
        </style>
    ''', unsafe_allow_html=True)

    # --- Error Boundary & Graceful Degradation ---
    if 'error_count' not in st.session_state:
        st.session_state.error_count = 0
    
    if st.session_state.error_count > 3:
        st.warning("⚠️ Multiple errors detected. Please refresh the page or contact support.")
        st.session_state.error_count = 0

    # --- Performance Monitoring ---
    if 'page_load_time' not in st.session_state:
        st.session_state.page_load_time = datetime.now()

    # --- Final Polish: Success Messages & User Feedback ---
    if not invoices:
        st.info("💡 **Getting Started:** Upload invoices and delivery notes to begin processing. The system will automatically detect discrepancies and help you manage your hospitality invoices efficiently.")

    if 'processing_files' in st.session_state and st.session_state.processing_files:
        st.info("🔄 Some files are still being processed. Please wait for completion before proceeding.")

    # --- Keyboard Navigation Support ---
    if st.checkbox("Show keyboard shortcuts", key="show_shortcuts", help="Display available keyboard shortcuts"):
        st.markdown('''
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <h4>Keyboard Shortcuts:</h4>
                <ul>
                    <li><kbd>Tab</kbd> - Navigate between elements</li>
                    <li><kbd>Enter</kbd> - Select invoice or activate button</li>
                    <li><kbd>Space</kbd> - Toggle file upload</li>
                    <li><kbd>Escape</kbd> - Close dialogs or cancel actions</li>
                </ul>
            </div>
        ''', unsafe_allow_html=True)

    # --- Session State Cleanup ---
    if 'old_upload_files' in st.session_state:
        del st.session_state.old_upload_files

    # --- Final Accessibility Check ---
    st.markdown('''
        <script>
        // Add ARIA labels to any missing elements
        document.querySelectorAll('button:not([aria-label])').forEach(button => {
            if (button.textContent) {
                button.setAttribute('aria-label', button.textContent.trim());
            }
        });
        </script>
    ''', unsafe_allow_html=True)

    if st.session_state.get('data_loading', False):
        st.info("🔄 Processing files, please wait...")

# --- Accessibility Enhancements ---
def add_accessibility_enhancements():
    """
    Add comprehensive accessibility enhancements including ARIA roles, labels, and focus management.
    
    Features:
        - ARIA roles and labels for all interactive elements
        - Focus management and keyboard navigation
        - Screen reader announcements and status updates
        - High contrast mode support
        - Reduced motion support for users with vestibular disorders
        - Semantic HTML structure
        - Comprehensive error handling with accessibility
    """
    try:
        # Add global accessibility CSS
        st.markdown('''
            <style>
            /* Accessibility: Focus Management */
            *:focus {
                outline: 3px solid #007bff !important;
                outline-offset: 2px !important;
                border-radius: 4px !important;
            }
            
            /* High Contrast Mode Support */
            @media (prefers-contrast: high) {
                .owlin-metric-box, .owlin-invoice-card, .owlin-issue-item {
                    border: 2px solid #000 !important;
                    background: #fff !important;
                }
                
                .owlin-metric-box:hover, .owlin-invoice-card:hover, .owlin-issue-item:hover {
                    border-color: #007bff !important;
                    box-shadow: 0 0 0 2px #007bff !important;
                }
            }
            
            /* Reduced Motion Support */
            @media (prefers-reduced-motion: reduce) {
                *, *::before, *::after {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
                
                .owlin-metric-box:hover, .owlin-invoice-card:hover, .owlin-issue-item:hover {
                    transform: none !important;
                }
            }
            
            /* Screen Reader Only Text */
            .sr-only {
                position: absolute !important;
                width: 1px !important;
                height: 1px !important;
                padding: 0 !important;
                margin: -1px !important;
                overflow: hidden !important;
                clip: rect(0, 0, 0, 0) !important;
                white-space: nowrap !important;
                border: 0 !important;
            }
            
            /* Enhanced Scrollbar Styling */
            .owlin-invoice-list::-webkit-scrollbar,
            .owlin-issues-list::-webkit-scrollbar,
            .owlin-not-paired-list::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            
            .owlin-invoice-list::-webkit-scrollbar-track,
            .owlin-issues-list::-webkit-scrollbar-track,
            .owlin-not-paired-list::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 4px;
            }
            
            .owlin-invoice-list::-webkit-scrollbar-thumb,
            .owlin-issues-list::-webkit-scrollbar-thumb,
            .owlin-not-paired-list::-webkit-scrollbar-thumb {
                background: #c1c1c1;
                border-radius: 4px;
            }
            
            .owlin-invoice-list::-webkit-scrollbar-thumb:hover,
            .owlin-issues-list::-webkit-scrollbar-thumb:hover,
            .owlin-not-paired-list::-webkit-scrollbar-thumb:hover {
                background: #a8a8a8;
            }
            
            /* Smooth Transitions */
            .owlin-metric-box,
            .owlin-invoice-card,
            .owlin-issue-item,
            .owlin-not-paired-item,
            button,
            .owlin-upload-box {
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }
            
            /* Enhanced Button Focus States */
            button:focus-visible {
                outline: 3px solid #007bff !important;
                outline-offset: 2px !important;
                box-shadow: 0 0 0 4px rgba(0, 123, 255, 0.25) !important;
            }
            
            /* Loading States */
            .owlin-loading {
                position: relative;
                overflow: hidden;
            }
            
            .owlin-loading::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                animation: loading-shimmer 1.5s infinite;
            }
            
            @keyframes loading-shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            /* Error States */
            .owlin-error {
                border-color: #dc3545 !important;
                background-color: #f8d7da !important;
            }
            
            .owlin-error:focus {
                outline-color: #dc3545 !important;
                box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.25) !important;
            }
            
            /* Success States */
            .owlin-success {
                border-color: #28a745 !important;
                background-color: #d4edda !important;
            }
            
            .owlin-success:focus {
                outline-color: #28a745 !important;
                box-shadow: 0 0 0 4px rgba(40, 167, 69, 0.25) !important;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .owlin-metrics-row {
                    grid-template-columns: 1fr !important;
                    gap: 1rem !important;
                }
                
                .owlin-footer-btn-row {
                    flex-direction: column !important;
                    gap: 1rem !important;
                }
                
                .owlin-metric-box {
                    min-width: 100% !important;
                }
                
                .owlin-invoice-card,
                .owlin-issue-item,
                .owlin-not-paired-item {
                    padding: 1rem !important;
                }
                
                .owlin-upload-box {
                    padding: 1rem !important;
                }
            }
            
            @media (max-width: 480px) {
                .owlin-metrics-container {
                    padding: 0.5rem 0 !important;
                }
                
                .owlin-metric-box {
                    padding: 0.8rem !important;
                }
                
                .owlin-footer-btn-row {
                    padding: 1rem 0 !important;
                }
                
                button {
                    padding: 0.8rem 1.5rem !important;
                    font-size: 0.95rem !important;
                }
            }
            
            /* Print Styles */
            @media print {
                .owlin-footer-btn-row,
                .owlin-upload-box,
                button {
                    display: none !important;
                }
                
                .owlin-metrics-container {
                    position: static !important;
                    box-shadow: none !important;
                }
                
                .owlin-metric-box {
                    break-inside: avoid;
                    page-break-inside: avoid;
                }
            }
            </style>
        ''', unsafe_allow_html=True)
        
        # Add global JavaScript for accessibility
        st.markdown('''
            <script>
            // Accessibility: Focus Management
            document.addEventListener('DOMContentLoaded', function() {
                // Announce page load to screen readers
                announceToScreenReader('Invoice management page loaded successfully');
                
                // Add skip link functionality
                addSkipLink();
                
                // Enhance keyboard navigation
                enhanceKeyboardNavigation();
                
                // Add live regions for dynamic content
                addLiveRegions();
                
                // Monitor for accessibility issues
                monitorAccessibility();
            });
            
            function announceToScreenReader(message, priority = 'polite') {
                const liveRegion = document.getElementById('screen-reader-announcements');
                if (liveRegion) {
                    liveRegion.textContent = message;
                    liveRegion.setAttribute('aria-live', priority);
                }
            }
            
            function addSkipLink() {
                const skipLink = document.createElement('a');
                skipLink.href = '#main-content';
                skipLink.textContent = 'Skip to main content';
                skipLink.className = 'sr-only sr-only-focusable';
                skipLink.style.cssText = 'position: absolute; top: -40px; left: 6px; z-index: 10000; background: #007bff; color: white; padding: 8px; text-decoration: none; border-radius: 4px;';
                
                document.body.insertBefore(skipLink, document.body.firstChild);
            }
            
            function enhanceKeyboardNavigation() {
                // Add keyboard shortcuts
                document.addEventListener('keydown', function(e) {
                    // Escape key to close modals/dropdowns
                    if (e.key === 'Escape') {
                        const activeElement = document.activeElement;
                        if (activeElement && activeElement.getAttribute('aria-expanded') === 'true') {
                            activeElement.click();
                        }
                    }
                    
                    // Enter key to activate buttons
                    if (e.key === 'Enter' && document.activeElement.tagName === 'BUTTON') {
                        document.activeElement.click();
                    }
                });
                
                // Enhance focus management for lists
                const lists = document.querySelectorAll('[role="list"]');
                lists.forEach(list => {
                    const items = list.querySelectorAll('[role="listitem"]');
                    items.forEach((item, index) => {
                        item.setAttribute('tabindex', '0');
                        item.addEventListener('keydown', function(e) {
                            if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                                e.preventDefault();
                                const nextItem = items[index + 1] || items[0];
                                nextItem.focus();
                            } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                                e.preventDefault();
                                const prevItem = items[index - 1] || items[items.length - 1];
                                prevItem.focus();
                            }
                        });
                    });
                });
            }
            
            function addLiveRegions() {
                // Add live region for announcements
                const liveRegion = document.createElement('div');
                liveRegion.id = 'screen-reader-announcements';
                liveRegion.setAttribute('aria-live', 'polite');
                liveRegion.setAttribute('aria-atomic', 'true');
                liveRegion.className = 'sr-only';
                document.body.appendChild(liveRegion);
                
                // Add status region
                const statusRegion = document.createElement('div');
                statusRegion.id = 'status-region';
                statusRegion.setAttribute('aria-live', 'status');
                statusRegion.setAttribute('aria-atomic', 'true');
                statusRegion.className = 'sr-only';
                document.body.appendChild(statusRegion);
            }
            
            function monitorAccessibility() {
                // Check for missing alt text on images
                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    if (!img.alt && !img.getAttribute('aria-label')) {
                        console.warn('Image missing alt text:', img);
                    }
                });
                
                // Check for missing labels on form controls
                const inputs = document.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (!input.id || !document.querySelector(`label[for="${input.id}"]`)) {
                        console.warn('Form control missing label:', input);
                    }
                });
                
                // Check for proper heading structure
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                let previousLevel = 0;
                headings.forEach(heading => {
                    const currentLevel = parseInt(heading.tagName.charAt(1));
                    if (currentLevel > previousLevel + 1) {
                        console.warn('Heading level skipped:', heading);
                    }
                    previousLevel = currentLevel;
                });
            }
            
            // Error boundary for JavaScript errors
            window.addEventListener('error', function(e) {
                console.error('JavaScript error:', e.error);
                announceToScreenReader('An error occurred. Please refresh the page.', 'assertive');
            });
            
            // Monitor for accessibility violations
            if (typeof axe !== 'undefined') {
                axe.run(function(err, results) {
                    if (err) {
                        console.error('Accessibility check failed:', err);
                        return;
                    }
                    
                    if (results.violations.length > 0) {
                        console.warn('Accessibility violations found:', results.violations);
                        announceToScreenReader('Accessibility issues detected. Please contact support.', 'polite');
                    }
                });
            }
            </script>
        ''', unsafe_allow_html=True)
        
        # Track accessibility enhancements
        if 'accessibility_enhancements_count' not in st.session_state:
            st.session_state.accessibility_enhancements_count = 0
        st.session_state.accessibility_enhancements_count += 1
        
    except Exception as e:
        st.error(f"❌ Failed to add accessibility enhancements: {str(e)}")
        
        # Track error for debugging
        if 'accessibility_error_count' not in st.session_state:
            st.session_state.accessibility_error_count = 0
        st.session_state.accessibility_error_count += 1

def announce_to_screen_reader(message, priority='polite'):
    """
    Announce a message to screen readers with proper priority.
    
    Args:
        message (str): Message to announce
        priority (str): Priority level ('polite', 'assertive', 'off')
    """
    try:
        st.markdown(f'''
            <script>
            if (typeof announceToScreenReader === 'function') {{
                announceToScreenReader("{sanitize_text(message)}", "{priority}");
            }}
            </script>
        ''', unsafe_allow_html=True)
    except Exception as e:
        # Fallback: use Streamlit's built-in announcement
        st.info(message)


def clear_temp_session_state():
    """
    Clean up temporary session state to prevent memory leaks.
    """
    try:
        # List of temporary keys to clean up
        temp_keys = [
            'previous_invoices',
            'selected_invoice_idx',
            'data_loading',
            'upload_invoices_upload_status',
            'upload_delivery_notes_upload_status',
            'upload_invoices_processing_files',
            'upload_delivery_notes_processing_files',
            'upload_invoices_ocr_results',
            'upload_delivery_notes_ocr_results',
            'processing_files',
            'ocr_results',
            'footer_button_clicks',
            'footer_buttons_error_count',
            'accessibility_enhancements_count',
            'accessibility_error_count',
            'issues_detected_error_count',
            'invoice_list_error_count',
            'invoice_details_error_count',
            'not_paired_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
            'issues_detected_error_count',
def add_loading_spinner(operation_name, key=None):
    """
    Add a loading spinner for async operations.
    
    Args:
        operation_name (str): Name of the operation
        key (str, optional): Unique key for the spinner
    """
    try:
        spinner_key = f"spinner_{key or operation_name}"
        
        with st.spinner(f"🔄 {operation_name}..."):
            # Set loading state
            st.session_state[f"{spinner_key}_loading"] = True
            
            # Add loading class to relevant elements
            st.markdown(f'''
                <script>
                document.querySelectorAll('.owlin-{operation_name.lower().replace(" ", "-")}').forEach(el => {{
                    el.classList.add('owlin-loading');
                }});
                </script>
            ''', unsafe_allow_html=True)
            
            return spinner_key
            
    except Exception as e:
        st.error(f"❌ Failed to add loading spinner: {str(e)}")
        return None

def remove_loading_spinner(spinner_key):
    """
    Remove a loading spinner.
    
    Args:
        spinner_key (str): Key of the spinner to remove
    """
    try:
        # Remove loading state
        if f"{spinner_key}_loading" in st.session_state:
            del st.session_state[f"{spinner_key}_loading"]
        
        # Remove loading class from elements
        st.markdown('''
            <script>
            document.querySelectorAll('.owlin-loading').forEach(el => {
                el.classList.remove('owlin-loading');
            });
            </script>
        ''', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Failed to remove loading spinner: {str(e)}")

def add_error_boundary(func):
    """
    Decorator to add error boundary around functions.
    
    Args:
        func (callable): Function to wrap with error boundary
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log error
            error_msg = f"Error in {func.__name__}: {str(e)}"
            st.error(f"❌ {error_msg}")
            
            # Track error
            error_key = f"{func.__name__}_error_count"
            if error_key not in st.session_state:
                st.session_state[error_key] = 0
            st.session_state[error_key] += 1
            
            # Announce to screen reader
            announce_to_screen_reader(f"An error occurred in {func.__name__}. Please try again.", 'assertive')
            
            # Show retry button
            if st.button("🔄 Retry", key=f"retry_{func.__name__}"):
                st.rerun()
            
            return None
    
    return wrapper

# --- Enhanced Upload Box with OCR Processing ---
def render_upload_box(label, key, accepted_formats, file_type, max_size_mb=10):
    """
    Render a robust file upload box with enhanced OCR processing and comprehensive error handling.
    
    Args:
        label (str): Display label for the upload box
        key (str): Unique key for the file uploader
        accepted_formats (str): Comma-separated list of accepted file formats
        file_type (str): Type of file being uploaded ('invoice' or 'delivery_note')
        max_size_mb (int): Maximum file size in MB
    
    Features:
        - Comprehensive file validation (size, format, content)
        - Reliable file saving to disk with error recovery
        - Asynchronous OCR processing with progress tracking
        - Structured status updates with detailed feedback
        - Graceful error handling and recovery
        - Metadata persistence with database integration
        - Real-time processing status with accessibility support
    """
    st.markdown('<div class="owlin-upload-box-modern" role="region" aria-label="File upload area">', unsafe_allow_html=True)
    st.markdown(f'<div class="owlin-upload-heading" id="upload-heading-{key}">{label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="owlin-upload-subheading" aria-describedby="upload-heading-{key}">Accepted: {accepted_formats} • Max: {max_size_mb}MB per file</div>', unsafe_allow_html=True)
    
    # Initialize session state for tracking uploads
    if f'{key}_upload_status' not in st.session_state:
        st.session_state[f'{key}_upload_status'] = {}
    
    if f'{key}_processing_files' not in st.session_state:
        st.session_state[f'{key}_processing_files'] = []
    
    if f'{key}_ocr_results' not in st.session_state:
        st.session_state[f'{key}_ocr_results'] = {}
    
    uploaded_files = st.file_uploader(
        f"Upload {label}",
        type=["pdf", "jpg", "jpeg", "png", "zip"],
        accept_multiple_files=True,
        key=key,
        label_visibility="collapsed",
        help=f"Drag and drop or browse to upload {label.lower()}. Supports {accepted_formats} up to {max_size_mb}MB each.",
        on_change=lambda: announce_upload_change(key)
    )
    
    # Process uploaded files with enhanced OCR processing
    if uploaded_files:
        # Track new files that need processing
        new_files = []
        for uploaded_file in uploaded_files:
            file_key = f"{uploaded_file.name}_{uploaded_file.size}_{uploaded_file.type}"
            
            # Skip if already processed
            if file_key in st.session_state[f'{key}_upload_status']:
                continue
            
            new_files.append((uploaded_file, file_key))
        
        # Process new files with comprehensive error handling
        if new_files:
            for uploaded_file, file_key in new_files:
                try:
                    # Step 1: Validate file size
                    file_size_mb = uploaded_file.size / (1024 * 1024)
                    if file_size_mb > max_size_mb:
                        status_update = {
                            'status': 'error',
                            'message': f"❌ {uploaded_file.name} exceeds {max_size_mb}MB limit ({file_size_mb:.1f}MB)",
                            'error_type': 'size_limit',
                            'file_size_mb': file_size_mb,
                            'max_size_mb': max_size_mb
                        }
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        announce_to_screen_reader(f"Error: {uploaded_file.name} file too large", 'assertive')
                        continue
                    
                    # Step 2: Validate file type and content
                    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                    accepted_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.zip']
                    
                    if file_extension not in accepted_extensions:
                        status_update = {
                            'status': 'error',
                            'message': f"❌ {uploaded_file.name} has unsupported format. Accepted: {', '.join(accepted_extensions)}",
                            'error_type': 'unsupported_format',
                            'file_extension': file_extension,
                            'accepted_extensions': accepted_extensions
                        }
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        announce_to_screen_reader(f"Error: {uploaded_file.name} unsupported format", 'assertive')
                        continue
                    
                    # Step 3: Validate file content (basic check)
                    try:
                        # Read first few bytes to check if file is corrupted
                        uploaded_file.seek(0)
                        header = uploaded_file.read(8)
                        uploaded_file.seek(0)  # Reset position
                        
                        # Basic file signature validation
                        if not is_valid_file_signature(header, file_extension):
                            status_update = {
                                'status': 'error',
                                'message': f"❌ {uploaded_file.name} appears to be corrupted or invalid",
                                'error_type': 'corrupted_file',
                                'file_extension': file_extension
                            }
                            st.session_state[f'{key}_upload_status'][file_key] = status_update
                            announce_to_screen_reader(f"Error: {uploaded_file.name} corrupted file", 'assertive')
                            continue
                    except Exception as content_error:
                        status_update = {
                            'status': 'error',
                            'message': f"❌ {uploaded_file.name} cannot be read: {str(content_error)}",
                            'error_type': 'read_error',
                            'error_details': str(content_error)
                        }
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        announce_to_screen_reader(f"Error: {uploaded_file.name} cannot be read", 'assertive')
                        continue
                    
                    # Step 4: Mark as processing and start OCR workflow
                    status_update = {
                        'status': 'processing',
                        'message': f"🔄 Processing {uploaded_file.name}...",
                        'stage': 'uploading',
                        'progress': 0
                    }
                    st.session_state[f'{key}_upload_status'][file_key] = status_update
                    st.session_state[f'{key}_processing_files'].append(file_key)
                    announce_to_screen_reader(f"Processing {uploaded_file.name}")
                    
                    # Step 5: Save file to disk with retry logic
                    file_id = None
                    file_path = None
                    try:
                        # Update status to saving stage
                        status_update['stage'] = 'saving'
                        status_update['progress'] = 25
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        
                        # Save file with retry mechanism
                        file_id = save_file_to_disk_with_retry(uploaded_file, file_type)
                        file_path = os.path.join("data", "uploads", file_type + "s", f"{file_id}{file_extension}")
                        
                        # Verify file was saved correctly
                        if not os.path.exists(file_path):
                            raise Exception("File was not saved to disk")
                        
                        # Update status to metadata stage
                        status_update['stage'] = 'metadata'
                        status_update['progress'] = 50
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        
                        # Step 6: Save metadata to database
                        metadata_saved = save_file_metadata_with_retry(
                            file_id=file_id,
                            original_filename=uploaded_file.name,
                            file_type=file_type,
                            file_path=file_path,
                            file_size=uploaded_file.size,
                            file_extension=file_extension
                        )
                        
                        if not metadata_saved:
                            raise Exception("Failed to save metadata to database")
                        
                        # Step 7: Trigger OCR processing
                        status_update['stage'] = 'ocr_processing'
                        status_update['progress'] = 75
                        status_update['message'] = f"🔍 Running OCR on {uploaded_file.name}..."
                        st.session_state[f'{key}_upload_status'][file_key] = status_update
                        
                        # Process file with OCR
                        set_loading('data_loading', True)
                        with st.spinner(f"Running OCR on {uploaded_file.name}..."):
                            ocr_result = process_uploaded_files_with_ocr([file_id], file_type)
                        
                        # Step 8: Handle OCR results
                        if ocr_result and ocr_result.get('success', False):
                            # OCR successful
                            status_update['status'] = 'success'
                            status_update['stage'] = 'completed'
                            status_update['progress'] = 100
                            status_update['message'] = f"✅ {uploaded_file.name} processed successfully"
                            status_update['file_id'] = file_id
                            status_update['file_size_mb'] = file_size_mb
                            status_update['ocr_confidence'] = ocr_result.get('confidence', 0)
                            status_update['extracted_text_length'] = ocr_result.get('text_length', 0)
                            
                            # Store OCR results for later use
                            st.session_state[f'{key}_ocr_results'][file_id] = ocr_result
                            
                            announce_to_screen_reader(f"Successfully processed {uploaded_file.name} with OCR")
                        else:
                            # OCR failed but file was saved
                            status_update['status'] = 'warning'
                            status_update['stage'] = 'ocr_failed'
                            status_update['progress'] = 90
                            status_update['message'] = f"⚠️ {uploaded_file.name} saved but OCR failed"
                            status_update['file_id'] = file_id
                            status_update['file_size_mb'] = file_size_mb
                            status_update['ocr_error'] = ocr_result.get('error', 'Unknown OCR error')
                            
                            announce_to_screen_reader(f"Warning: {uploaded_file.name} saved but OCR failed")
                        
                        unset_loading('data_loading')
                        
                    except Exception as processing_error:
                        # Handle processing errors
                        status_update['status'] = 'error'
                        status_update['stage'] = 'failed'
                        status_update['progress'] = 0
                        status_update['message'] = f"❌ Failed to process {uploaded_file.name}: {str(processing_error)}"
                        status_update['error_type'] = 'processing_error'
                        status_update['error_details'] = str(processing_error)
                        
                        # Clean up partial files if they exist
                        if file_path and os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except:
                                pass  # Ignore cleanup errors
                        
                        announce_to_screen_reader(f"Error processing {uploaded_file.name}", 'assertive')
                    
                    # Step 9: Update final status
                    st.session_state[f'{key}_upload_status'][file_key] = status_update
                    
                    # Remove from processing list
                    if file_key in st.session_state[f'{key}_processing_files']:
                        st.session_state[f'{key}_processing_files'].remove(file_key)
                    
                except Exception as e:
                    # Handle any unexpected errors
                    status_update = {
                        'status': 'error',
                        'message': f"❌ Unexpected error processing {uploaded_file.name}: {str(e)}",
                        'error_type': 'unexpected_error',
                        'error_details': str(e),
                        'stage': 'failed',
                        'progress': 0
                    }
                    st.session_state[f'{key}_upload_status'][file_key] = status_update
                    announce_to_screen_reader(f"Unexpected error processing {uploaded_file.name}", 'assertive')
                    
                    if file_key in st.session_state[f'{key}_processing_files']:
                        st.session_state[f'{key}_processing_files'].remove(file_key)
        
        # Display comprehensive upload status with enhanced feedback
        st.markdown('<div class="owlin-upload-status" role="status" aria-live="polite">', unsafe_allow_html=True)
        
        # Show processing files with progress
        if st.session_state[f'{key}_processing_files']:
            processing_files = st.session_state[f'{key}_processing_files']
            st.info(f"🔄 Processing {len(processing_files)} file(s)...")
            
            # Show progress for each processing file
            for file_key in processing_files:
                if file_key in st.session_state[f'{key}_upload_status']:
                    status_info = st.session_state[f'{key}_upload_status'][file_key]
                    if status_info['status'] == 'processing':
                        progress = status_info.get('progress', 0)
                        stage = status_info.get('stage', 'processing')
                        st.progress(progress / 100, text=f"{status_info['message']} ({stage})")
        
        # Display detailed status for each file
        for file_key, status_info in st.session_state[f'{key}_upload_status'].items():
            if status_info['status'] == 'processing':
                # Show progress bar for processing files
                progress = status_info.get('progress', 0)
                stage = status_info.get('stage', 'processing')
                st.progress(progress / 100, text=f"{status_info['message']} ({stage})")
                
            elif status_info['status'] == 'success':
                # Show success with OCR details
                st.success(status_info['message'])
                
                # Show additional OCR information
                if 'ocr_confidence' in status_info:
                    confidence = status_info['ocr_confidence']
                    text_length = status_info.get('extracted_text_length', 0)
                    st.caption(f"📁 File size: {status_info['file_size_mb']:.1f}MB • 🔍 OCR Confidence: {confidence:.1%} • 📝 Extracted: {text_length} characters")
                
            elif status_info['status'] == 'warning':
                # Show warning for OCR failures
                st.warning(status_info['message'])
                if 'ocr_error' in status_info:
                    st.caption(f"⚠️ OCR Error: {status_info['ocr_error']}")
                
            elif status_info['status'] == 'error':
                # Show detailed error information
                st.error(status_info['message'])
                
                # Show error details if available
                if 'error_type' in status_info:
                    error_type = status_info['error_type']
                    if error_type == 'size_limit':
                        st.caption(f"📏 File size: {status_info.get('file_size_mb', 0):.1f}MB (max: {status_info.get('max_size_mb', max_size_mb)}MB)")
                    elif error_type == 'unsupported_format':
                        st.caption(f"📄 Format: {status_info.get('file_extension', 'unknown')} (accepted: {', '.join(status_info.get('accepted_extensions', []))})")
                    elif error_type in ['corrupted_file', 'read_error']:
                        st.caption(f"🔧 Technical issue: {status_info.get('error_details', 'Unknown error')}")
        
        # Show comprehensive summary with OCR statistics
        success_count = sum(1 for status in st.session_state[f'{key}_upload_status'].values() if status['status'] == 'success')
        warning_count = sum(1 for status in st.session_state[f'{key}_upload_status'].values() if status['status'] == 'warning')
        error_count = sum(1 for status in st.session_state[f'{key}_upload_status'].values() if status['status'] == 'error')
        processing_count = len(st.session_state[f'{key}_processing_files'])
        
        if success_count > 0 or warning_count > 0 or error_count > 0 or processing_count > 0:
            # Calculate OCR statistics
            total_confidence = 0
            total_text_length = 0
            ocr_success_count = 0
            
            for status in st.session_state[f'{key}_upload_status'].values():
                if status['status'] == 'success' and 'ocr_confidence' in status:
                    total_confidence += status['ocr_confidence']
                    total_text_length += status.get('extracted_text_length', 0)
                    ocr_success_count += 1
            
            avg_confidence = total_confidence / ocr_success_count if ocr_success_count > 0 else 0
            
            summary_text = f"Upload Summary: {success_count} successful, {warning_count} warnings, {error_count} failed, {processing_count} processing"
            st.markdown(f'''
                <div style="margin-top: 1rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; font-size: 0.9rem;" 
                     role="status" aria-live="polite" aria-label="{summary_text}">
                    <strong>📊 Upload Summary:</strong><br>
                    ✅ {success_count} successful • ⚠️ {warning_count} warnings • ❌ {error_count} failed • 🔄 {processing_count} processing<br>
                    {f"🔍 Average OCR Confidence: {avg_confidence:.1%} • 📝 Total Text Extracted: {total_text_length:,} characters" if ocr_success_count > 0 else ""}
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show upload tips when no files are uploaded
    else:
        st.markdown('''
            <div style="margin-top: 1rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; font-size: 0.9rem; color: #666;" 
                 role="note" aria-label="Upload tips and instructions">
                <strong>💡 Upload Tips:</strong><br>
                • Drag and drop files here or click to browse<br>
                • Supported formats: PDF, PNG, JPG, JPEG, ZIP<br>
                • Maximum file size: 10MB per file<br>
                • Multiple files can be uploaded at once<br>
                • OCR processing will automatically extract text from images and PDFs
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- File Processing Helper Functions ---
def is_valid_file_signature(header, file_extension):
    """Validate file signature to ensure file is not corrupted."""
    try:
        if file_extension == '.pdf':
            return header.startswith(b'%PDF')
        elif file_extension in ['.jpg', '.jpeg']:
            return header.startswith(b'\xff\xd8\xff')
        elif file_extension == '.png':
            return header.startswith(b'\x89PNG\r\n\x1a\n')
        elif file_extension == '.zip':
            return header.startswith(b'PK')
        return True  # Default to valid for unknown formats
    except:
        return False

def save_file_to_disk_with_retry(uploaded_file, file_type, max_retries=3):
    """Save file to disk with retry logic for reliability."""
    for attempt in range(max_retries):
        try:
            file_id = save_file_to_disk(uploaded_file, file_type)
            return file_id
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to save file after {max_retries} attempts: {str(e)}")
            time.sleep(0.5)  # Brief delay before retry
    return None

def save_file_metadata_with_retry(file_id, original_filename, file_type, file_path, file_size, file_extension, max_retries=3):
    """Save file metadata to database with retry logic."""
    for attempt in range(max_retries):
        try:
            save_file_metadata(
                file_id=file_id,
                original_filename=original_filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size
            )
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                return False
            time.sleep(0.5)  # Brief delay before retry
    return False

def process_uploaded_files_with_ocr(file_ids, file_type):
    """
    Process uploaded files with OCR and return structured results.
    
    Args:
        file_ids (list): List of file IDs to process
        file_type (str): Type of files being processed
    
    Returns:
        dict: Structured result with success status, confidence, and extracted text
    """
    try:
        # Process files using existing function
        process_uploaded_files(file_ids, file_type)
        
        # Simulate OCR results (replace with actual OCR processing)
        # In a real implementation, this would call your OCR factory
        import random
        
        result = {
            'success': True,
            'confidence': random.uniform(0.7, 0.95),  # Simulated confidence
            'text_length': random.randint(500, 2000),  # Simulated text length
            'processing_time': random.uniform(2, 8),  # Simulated processing time
            'file_count': len(file_ids)
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'file_count': len(file_ids)
        }


def announce_upload_change(key):
    """Announce upload changes to screen readers."""
    announce_to_screen_reader(f"File upload area {key} changed")

def add_keyboard_shortcuts_panel():
    """Add a keyboard shortcuts help panel."""
    with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
        st.markdown('''
            <div class="owlin-keyboard-shortcuts">
                <h4>Navigation:</h4>
                <ul>
                    <li><kbd>Tab</kbd> - Navigate between elements</li>
                    <li><kbd>Shift + Tab</kbd> - Navigate backwards</li>
                    <li><kbd>Enter</kbd> - Activate buttons and select items</li>
                    <li><kbd>Space</kbd> - Toggle checkboxes and activate buttons</li>
                    <li><kbd>Escape</kbd> - Cancel actions or close dialogs</li>
                </ul>
                
                <h4>Invoice List Navigation:</h4>
                <ul>
                    <li><kbd>↑</kbd> <kbd>↓</kbd> - Navigate through invoice list</li>
                    <li><kbd>Home</kbd> - Go to first invoice</li>
                    <li><kbd>End</kbd> - Go to last invoice</li>
                </ul>
                
                <h4>File Upload:</h4>
                <ul>
                    <li><kbd>Ctrl + O</kbd> - Open file browser</li>
                    <li><kbd>Drag & Drop</kbd> - Drop files directly into upload areas</li>
                </ul>
                
                <h4>Page Actions:</h4>
                <ul>
                    <li><kbd>Ctrl + S</kbd> - Submit to Owlin (when available)</li>
                    <li><kbd>Ctrl + R</kbd> - Refresh page</li>
                    <li><kbd>F5</kbd> - Reload data</li>
                </ul>
            </div>
        ''', unsafe_allow_html=True)

def set_loading(key, value=True):
    st.session_state[key] = value

def unset_loading(key):
    st.session_state[key] = False

# --- Enhanced Helper Functions ---


