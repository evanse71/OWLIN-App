#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal invoice upload interface with dual drag-and-drop zones."""

import streamlit as st
from datetime import datetime


def render_drop_box(label: str, key: str, icon: str, files=None):
    """
    Render a reusable drop box with file display.
    
    Args:
        label: Display label for the upload box
        key: Unique key for the file uploader
        icon: Emoji icon to display
        files: List of uploaded files to display
    """
    st.markdown(
        f"""
        <div class="drop-box" id="{key}_box">
            <div class="upload-icon">{icon}</div>
            <div class="upload-label">{label}</div>
            <div class="upload-sub">PDF, PNG, JPG, JPEG · Max 10MB</div>
            <button class="browse-btn" onclick="window.trigger{key.capitalize()}Upload && window.trigger{key.capitalize()}Upload()" aria-label="Browse {label.lower()} files">Browse Files</button>
        """,
        unsafe_allow_html=True,
    )
    
    # Display uploaded files inside the drop box
    if files:
        st.markdown('<div class="file-list">', unsafe_allow_html=True)
        for file in files:
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.markdown(
                f'<div class="file-item">📄 {file.name} <span style="color:#94a3b8;">{timestamp}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_upload_panel():
    """Render two side-by-side upload boxes with drag-and-drop support."""

    st.markdown(
        """
        <style>
            body, .stApp {background-color:#f8f9fb;}
            .block-container {padding-top: 2rem; padding-bottom: 2rem;}
            .upload-wrapper{max-width:1200px;margin:0 auto;padding:0 2rem;}
            .dual-zone{display:flex;gap:2rem;margin-top:2.5rem;margin-bottom:3rem;}
            @media (max-width:768px){.dual-zone{flex-direction:column;}}
            .drop-box{flex:1;min-width:320px;max-width:600px;min-height:220px;background:rgba(255,255,255,0.95);border:2px dashed rgba(100,116,139,0.3);border-radius:20px;box-shadow:0 4px 30px rgba(0,0,0,0.05);padding:2rem;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;transition:transform .2s,border-color .2s;}
            .drop-box:hover{transform:scale(1.02);border-color:#2563eb;}
            .upload-icon{font-size:2.5rem;margin-bottom:0.8rem;opacity:0.7;}
            .upload-label{font-size:1.1rem;font-weight:600;color:#1e293b;margin-bottom:0.3rem;}
            .upload-sub{font-size:0.9rem;color:#64748b;margin-bottom:1rem;text-align:center;line-height:1.4;}
            .browse-btn{background:#2563eb;color:#fff;border:none;padding:0.6rem 1.3rem;border-radius:8px;font-size:0.9rem;font-weight:500;cursor:pointer;transition:transform .2s;background-clip:padding-box;box-shadow:0 2px 8px rgba(37,99,235,0.2);} 
            .browse-btn:hover{background:#1d4ed8;transform:translateY(-1px);} 
            .hidden-uploader{display:none !important;} 
            .file-list{margin-top:1rem;width:100%;font-size:0.9rem;} 
            .file-item{display:flex;justify-content:space-between;border-bottom:1px solid #e9ecef;padding:0.25rem 0;} 
            #global-drop{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(37,99,235,0.1);border:3px dashed rgba(37,99,235,0.6);z-index:9999;display:none;align-items:center;justify-content:center;font-size:1.5rem;font-weight:600;color:#2563eb;animation:dragPulse 1.5s ease-in-out infinite;pointer-events:none;} 
            @keyframes dragPulse{0%,100%{opacity:0.3;transform:scale(1);}50%{opacity:0.8;transform:scale(1.02);}}
            .invoice-container{background:#fff;border-radius:20px;padding:2rem;box-shadow:0 6px 24px rgba(0,0,0,0.04);margin-top:2rem;max-width:1200px;padding:0 2rem;margin:0 auto;}
        </style>
        <div id="global-drop">Drop files to upload</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="upload-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="dual-zone">', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        # Invoice upload box
        render_drop_box("Drop your invoices here", "invoice", "📄")
        invoice_files = st.file_uploader(
            "Invoice Upload",
            type=["pdf", "png", "jpg", "jpeg"],
            key="invoice_upload",
            label_visibility="collapsed",
            accept_multiple_files=True,
        )
        
    with col2:
        # Delivery note upload box
        render_drop_box("Drop your delivery notes here", "delivery", "📋")
        delivery_files = st.file_uploader(
            "Delivery Upload",
            type=["pdf", "png", "jpg", "jpeg"],
            key="delivery_upload",
            label_visibility="collapsed",
            accept_multiple_files=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <script>
            let invoiceInput=null; let deliveryInput=null; let initDone=false;
            function findInputs(){const inputs=document.querySelectorAll('input[type="file"]');if(inputs.length>=2){invoiceInput=inputs[0];deliveryInput=inputs[1];return true;}return false;}
            function init(){if(initDone)return;if(!findInputs()){setTimeout(init,200);}else{initDone=true;}}
            function triggerInvoice(){if(invoiceInput){invoiceInput.click();}}
            function triggerDelivery(){if(deliveryInput){deliveryInput.click();}}
            function setupDnD(){const body=document.body;const overlay=document.getElementById('global-drop');['dragenter','dragover','dragleave','drop'].forEach(n=>body.addEventListener(n,e=>{e.preventDefault();e.stopPropagation();},false));
                ['dragenter','dragover'].forEach(n=>body.addEventListener(n,()=>{overlay.style.display='flex';},false));
                body.addEventListener('dragleave',e=>{if(e.clientX<=0||e.clientY<=0||e.clientX>=window.innerWidth||e.clientY>=window.innerHeight){overlay.style.display='none';}},false);
                body.addEventListener('drop',e=>{overlay.style.display='none';const files=e.dataTransfer.files;if(!files.length)return;const target=e.clientX<window.innerWidth/2?invoiceInput:deliveryInput;if(!target){return;}const dt=new DataTransfer();for(let i=0;i<files.length;i++){dt.items.add(files[i]);}target.files=dt.files;const evt=new Event('change',{bubbles:true});target.dispatchEvent(evt);},false);
            }
            if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',()=>{init();setupDnD();});}else{init();setupDnD();}
            window.triggerInvoiceUpload=triggerInvoice;window.triggerDeliveryUpload=triggerDelivery;
        </script>
        """,
        unsafe_allow_html=True,
    )

    return invoice_files, delivery_files


def render_invoices_page():
    """Render the invoices upload page."""
    invoice_files, delivery_files = render_upload_panel()

    # Show uploaded files in separate sections
    if invoice_files:
        st.markdown("<div class='file-list'>", unsafe_allow_html=True)
        st.markdown("<h5>📄 Uploaded Invoices:</h5>", unsafe_allow_html=True)
        for f in invoice_files:
            ts = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"<div class='file-item'><span>{f.name}</span><span>{ts}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if delivery_files:
        st.markdown("<div class='file-list'>", unsafe_allow_html=True)
        st.markdown("<h5>📋 Uploaded Delivery Notes:</h5>", unsafe_allow_html=True)
        for f in delivery_files:
            ts = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"<div class='file-item'><span>{f.name}</span><span>{ts}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Show placeholder or content in white container
    if not invoice_files and not delivery_files:
        st.markdown(
            """
            <div class="invoice-container">
                <div style="text-align:center;padding:2rem;color:#94a3b8;">
                    📂 No invoices uploaded yet. Once you upload files, they will appear here.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="invoice-container">
                <div style="text-align:center;color:#94a3b8;font-size:0.95rem;">Uploaded invoices will appear here…</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render_invoices_page() 