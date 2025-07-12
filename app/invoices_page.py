#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# [NOTE] Invoice upload UI is now handled in React (see components/invoices/InvoicesUploadPanel.tsx)
# This file retains imports, comments, and constants for potential reuse.

# =====================
# [DISABLED] Streamlit UI migrated to React/Next.js
# See: /components/invoices/InvoicesUploadPanel.tsx
# =====================
# def render_upload_panel():
#     """
#     Render a structured dual-upload panel with invoices and delivery notes.
#     
#     Features:
#     - Two side-by-side upload boxes with glass styling
#     - Custom "Browse Files" buttons for each uploader
#     - Full-page drag-and-drop with left/right routing
#     - Hidden Streamlit uploaders with proper linking
#     - Clean file summary display with timestamps
#     
#     Returns:
#         tuple: (invoice_files, delivery_files) - StreamlitUploadedFile objects
#     """
#     
#     # ============================================================================
#     # 1. GLOBAL STYLES AND DRAG OVERLAY
#     # ============================================================================
#     
#     st.markdown("""
#     <style>
#         /* Light grey page background */
#         body, .block-container {
#             background-color: #f8f9fa !important;
#         }
#         
#         /* Hide default Streamlit uploaders */
#         .stFileUploader { 
#             display: none !important; 
#         }
#         
#         /* Upload container layout */
#         .upload-container {
#             max-width: 1200px;
#             margin: 0 auto;
#             padding: 2rem 1.5rem;
#         }
#         
#         /* Glass box styling for upload areas */
#         .owlin-glass-box {
#             background: rgba(255, 255, 255, 0.95);
#             backdrop-filter: blur(20px);
#             -webkit-backdrop-filter: blur(20px);
#             border: 2px dashed rgba(100, 116, 139, 0.4);
#             border-radius: 16px;
#             padding: 2.5rem;
#             text-align: center;
#             transition: all 0.3s ease;
#             box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
#             min-height: 220px;
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#             justify-content: center;
#         }
#         
#         .owlin-glass-box:hover {
#             border-color: rgba(37, 99, 235, 0.6);
#             box-shadow: 0 8px 40px rgba(37, 99, 235, 0.15);
#             transform: translateY(-2px);
#         }
#         
#         /* Upload box content styling */
#         .upload-icon {
#             font-size: 2.5rem;
#             margin-bottom: 1rem;
#             opacity: 0.7;
#         }
#         
#         .upload-title {
#             font-size: 1.15rem;
#             font-weight: 600;
#             color: #1e293b;
#             margin-bottom: 0.5rem;
#         }
#         
#         .upload-subtitle {
#             font-size: 0.9rem;
#             color: #64748b;
#             margin-bottom: 1.5rem;
#             line-height: 1.4;
#         }
#         
#         /* Custom browse button styling */
#         .owlin-browse-btn {
#             background: #2563eb;
#             color: white;
#             border: none;
#             padding: 0.75rem 1.5rem;
#             border-radius: 8px;
#             font-size: 0.9rem;
#             font-weight: 500;
#             cursor: pointer;
#             transition: all 0.2s ease;
#             box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
#         }
#         
#         .owlin-browse-btn:hover {
#             background: #1d4ed8;
def render_upload_panel():
    """
    Render a structured dual-upload panel with invoices and delivery notes.
    
    Features:
    - Two side-by-side upload boxes with glass styling
    - Custom "Browse Files" buttons for each uploader
    - Full-page drag-and-drop with left/right routing
    - Hidden Streamlit uploaders with proper linking
    - Clean file summary display with timestamps
    
    Returns:
        tuple: (invoice_files, delivery_files) - StreamlitUploadedFile objects
    """
    
    # ============================================================================
    # 1. GLOBAL STYLES AND DRAG OVERLAY
    # ============================================================================
    
    st.markdown("""
    <style>
        /* Light grey page background */
        body, .block-container {
            background-color: #f8f9fa !important;
        }
        
        /* Hide default Streamlit uploaders */
        .stFileUploader { 
            display: none !important; 
        }
        
        /* Upload container layout */
        .upload-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }
        
        /* Glass box styling for upload areas */
        .owlin-glass-box {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 2px dashed rgba(100, 116, 139, 0.4);
            border-radius: 16px;
            padding: 2.5rem;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
            min-height: 220px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .owlin-glass-box:hover {
            border-color: rgba(37, 99, 235, 0.6);
            box-shadow: 0 8px 40px rgba(37, 99, 235, 0.15);
            transform: translateY(-2px);
        }
        
        /* Upload box content styling */
        .upload-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            opacity: 0.7;
        }
        
        .upload-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 0.5rem;
        }
        
        .upload-subtitle {
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 1.5rem;
            line-height: 1.4;
        }
        
        /* Custom browse button styling */
        .owlin-browse-btn {
            background: #2563eb;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
        }
        
        .owlin-browse-btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }
        
        /* Global drag overlay */
        #global-drop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(37, 99, 235, 0.1);
            border: 3px dashed rgba(37, 99, 235, 0.6);
            z-index: 9999;
            pointer-events: none;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 600;
            color: #2563eb;
            animation: dragPulse 1.5s ease-in-out infinite;
        }
        
        @keyframes dragPulse {
            0%, 100% { 
                opacity: 0.3;
                transform: scale(1);
            }
            50% { 
                opacity: 0.8;
                transform: scale(1.02);
            }
        }
        
        /* File summary styling */
        .file-summary {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-name {
            font-weight: 500;
            color: #1e293b;
        }
        
        .file-time {
            font-size: 0.8rem;
            color: #64748b;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .upload-container {
                padding: 1rem;
            }
            .owlin-glass-box {
                padding: 2rem;
                min-height: 200px;
            }
        }
    </style>
    
    <!-- Global drag overlay element -->
    <div id="global-drop">Drop files to upload</div>
    """, unsafe_allow_html=True)
    
    # ============================================================================
    # 2. UPLOAD BOX UI CONTAINERS
    # ============================================================================
    
    st.markdown('<div class="upload-container">', unsafe_allow_html=True)
    
    # Create two columns for side-by-side upload boxes
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        # Invoice upload box
        st.markdown("""
        <div class="owlin-glass-box" id="invoice_upload_box">
            <div class="upload-icon">📄</div>
            <div class="upload-title">Upload Invoices</div>
            <div class="upload-subtitle">PDF, PNG, JPG, JPEG files<br>Max 10MB per file</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Custom browse button for invoices
        if st.button("Browse Files", key="invoice_select_btn", use_container_width=True):
            st.session_state.trigger_invoice_upload = True
        
        # Hidden file uploader for invoices
        invoice_files = st.file_uploader(
            "Upload Invoices",
            type=["pdf", "jpg", "jpeg", "png"],
            key="invoice_upload_box",
            label_visibility="collapsed",
            accept_multiple_files=True,
            help="Upload invoice files"
        )
    
    with col2:
        # Delivery note upload box
        st.markdown("""
        <div class="owlin-glass-box" id="delivery_upload_box">
            <div class="upload-icon">📋</div>
            <div class="upload-title">Upload Delivery Notes</div>
            <div class="upload-subtitle">PDF, PNG, JPG, JPEG files<br>Max 10MB per file</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Custom browse button for delivery notes
        if st.button("Browse Files", key="delivery_select_btn", use_container_width=True):
            st.session_state.trigger_delivery_upload = True
        
        # Hidden file uploader for delivery notes
        delivery_files = st.file_uploader(
            "Upload Delivery Notes",
            type=["pdf", "jpg", "jpeg", "png"],
            key="delivery_upload_box",
            label_visibility="collapsed",
            accept_multiple_files=True,
            help="Upload delivery note files"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ============================================================================
    # 3. JAVASCRIPT BUTTON LINKING LOGIC
    # ============================================================================
    
    st.markdown("""
    <script>
        // Global variables for file inputs
        let invoiceFileInput = null;
        let deliveryFileInput = null;
        let isInitialized = false;
        
        // Function to find file inputs by data-testid
        function findFileInputs() {
            const inputs = document.querySelectorAll('input[type="file"]');
            console.log('Found file inputs:', inputs.length);
            
            if (inputs.length >= 2) {
                invoiceFileInput = inputs[0];
                deliveryFileInput = inputs[1];
                console.log('File inputs assigned successfully');
                return true;
            }
            return false;
        }
        
        // Initialize file inputs with retry mechanism
        function initializeFileInputs() {
            if (isInitialized) return;
            
            if (!findFileInputs()) {
                console.log('File inputs not found, retrying...');
                setTimeout(initializeFileInputs, 200);
            } else {
                isInitialized = true;
                console.log('File inputs initialized successfully');
            }
        }
        
        // Click handlers for custom browse buttons
        function triggerInvoiceUpload() {
            console.log('Triggering invoice upload');
            if (invoiceFileInput) {
                invoiceFileInput.click();
            } else {
                console.log('Invoice file input not found, trying to find it...');
                findFileInputs();
                if (invoiceFileInput) {
                    invoiceFileInput.click();
                }
            }
        }
        
        function triggerDeliveryUpload() {
            console.log('Triggering delivery upload');
            if (deliveryFileInput) {
                deliveryFileInput.click();
            } else {
                console.log('Delivery file input not found, trying to find it...');
                findFileInputs();
                if (deliveryFileInput) {
                    deliveryFileInput.click();
                }
            }
        }
        
        // Full-page drag and drop functionality
        function setupDragAndDrop() {
            const body = document.body;
            const globalDrop = document.getElementById('global-drop');
            
            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                body.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            // Handle drag enter and over
            ['dragenter', 'dragover'].forEach(eventName => {
                body.addEventListener(eventName, highlight, false);
            });
            
            function highlight(e) {
                globalDrop.style.display = 'flex';
                console.log('Drag detected');
            }
            
            // Handle drag leave
            body.addEventListener('dragleave', unhighlight, false);
            
            function unhighlight(e) {
                // Only hide overlay if leaving the window entirely
                if (e.clientX <= 0 || e.clientY <= 0 || 
                    e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
                    globalDrop.style.display = 'none';
                    console.log('Drag leave detected');
                }
            }
            
            // Handle drop
            body.addEventListener('drop', handleDrop, false);
            
            function handleDrop(e) {
                globalDrop.style.display = 'none';
                console.log('Drop detected');
                
                const files = e.dataTransfer.files;
                if (files.length === 0) return;
                
                console.log('Files dropped:', files.length);
                
                // Determine which uploader to use based on drop position
                const dropX = e.clientX;
                const windowWidth = window.innerWidth;
                const isLeftSide = dropX < windowWidth / 2;
                
                const targetInput = isLeftSide ? invoiceFileInput : deliveryFileInput;
                const uploadType = isLeftSide ? 'invoice' : 'delivery';
                
                console.log('Targeting uploader:', uploadType);
                
                if (targetInput) {
                    try {
                        // Use DataTransfer to copy files
                        const dataTransfer = new DataTransfer();
                        for (let i = 0; i < files.length; i++) {
                            dataTransfer.items.add(files[i]);
                        }
                        
                        // Set files on target input
                        targetInput.files = dataTransfer.files;
                        
                        // Trigger change event
                        const changeEvent = new Event('change', { bubbles: true });
                        targetInput.dispatchEvent(changeEvent);
                        
                        console.log('Files successfully transferred to', uploadType, 'uploader');
                    } catch (error) {
                        console.log('File transfer failed, falling back to click:', error);
                        targetInput.click();
                    }
                } else {
                    console.log('Target input not found');
                }
            }
        }
        
        // Initialize everything when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                initializeFileInputs();
                setupDragAndDrop();
            });
        } else {
            initializeFileInputs();
            setupDragAndDrop();
        }
        
        // Additional initialization after a delay
        setTimeout(function() {
            if (!isInitialized) {
                console.log('Delayed initialization');
                initializeFileInputs();
            }
        }, 1000);
        
        // Make functions globally available
        window.triggerInvoiceUpload = triggerInvoiceUpload;
        window.triggerDeliveryUpload = triggerDeliveryUpload;
    </script>
    """, unsafe_allow_html=True)
    
    # ============================================================================
    # 4. UPLOADED FILE SUMMARY DISPLAY
    # ============================================================================
    
    # Handle button triggers
    if st.session_state.get('trigger_invoice_upload', False):
        st.markdown("""
        <script>
            if (window.triggerInvoiceUpload) {
                window.triggerInvoiceUpload();
            }
        </script>
        """, unsafe_allow_html=True)
        st.session_state.trigger_invoice_upload = False
    
    if st.session_state.get('trigger_delivery_upload', False):
        st.markdown("""
        <script>
            if (window.triggerDeliveryUpload) {
                window.triggerDeliveryUpload();
            }
        </script>
        """, unsafe_allow_html=True)
        st.session_state.trigger_delivery_upload = False
    
    # Display file summaries
    if invoice_files or delivery_files:
        st.markdown('<div class="file-summary">', unsafe_allow_html=True)
        st.markdown('<h4>📁 Uploaded Files</h4>', unsafe_allow_html=True)
        
        if invoice_files:
            st.markdown('<h5>📄 Invoices:</h5>', unsafe_allow_html=True)
            for file in invoice_files:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.markdown(f"""
                <div class="file-item">
                    <span class="file-name">{file.name}</span>
                    <span class="file-time">{timestamp}</span>
                </div>
                """, unsafe_allow_html=True)
        
        if delivery_files:
            st.markdown('<h5>📋 Delivery Notes:</h5>', unsafe_allow_html=True)
            for file in delivery_files:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.markdown(f"""
                <div class="file-item">
                    <span class="file-name">{file.name}</span>
                    <span class="file-time">{timestamp}</span>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    return invoice_files, delivery_files
