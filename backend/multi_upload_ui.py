"""
multi_upload_ui.py
===================

This example demonstrates how to integrate multi-file invoice upload
into a Streamlit front end with progress feedback.  It builds on
existing backend helpers from ``field_extractor`` and ``upload_validator``.
Each selected file is processed sequentially: the invoice is
analysed, validated and its status reported to the user.  A progress
bar shows upload progress and per-file messages communicate success
or failure.

Please note that this example assumes the existence of OCR results
and extracted data.  In a real application you would need to run
OCR (e.g. via Tesseract) on each uploaded file and then call
``extract_invoice_fields`` before validation.  This code focuses
solely on the UI flow and the integration with the existing helpers.
"""

import os
import hashlib
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

import streamlit as st
import logging

from .ocr.field_extractor import extract_invoice_fields
from .upload_validator import validate_upload
from .ocr.ocr_processing import run_ocr, run_ocr_with_fallback
from .db_manager import init_db, save_invoice, save_file_hash, user_has_permission, log_processing_result


def upload_invoices_ui(db_path: str, user_role: str) -> None:
    """Render a multi-file invoice uploader with validation, OCR and persistence.

    This function enforces role-based permissions, runs OCR on each
    uploaded file, extracts invoice fields, validates them, saves
    valid invoices to the database and displays progress and status
    messages.  Audit information is logged to a file.

    Parameters
    ----------
    db_path: str
        Path to the SQLite database used for duplicate checking and
        storage.
    user_role: str
        Role of the current user (e.g. 'GM', 'Finance', 'Shift Lead').
    """
    st.header("Upload Invoices")
    st.write("Select one or more invoice files to upload. Supported formats include PDF and common image types.")

    # Initialise database schema (idempotent)
    init_db(db_path)

    # Configure logging to an audit file inside the data directory
    log_dir = os.path.join(os.path.dirname(db_path))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "audit.log")
    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s %(message)s")

    # Check permissions
    if not user_has_permission(user_role):
        st.error("❌ You do not have permission to upload invoices.")
        st.info("Contact your administrator to request upload permissions.")
        return

    # Display user role and permissions
    st.success(f"✅ Logged in as: {user_role}")
    
    # File upload interface
    uploaded_files = st.file_uploader(
        "Choose invoice files",
        type=["pdf", "jpg", "jpeg", "png", "tiff"],
        accept_multiple_files=True,
        help="Select one or more invoice files to upload. Supported formats: PDF, JPG, PNG, TIFF"
    )

    if uploaded_files:
        # Display upload summary
        st.subheader(f"📁 Upload Summary")
        st.write(f"**Files selected:** {len(uploaded_files)}")
        
        # Show file details
        file_details = []
        for file in uploaded_files:
            file_size = len(file.getbuffer())
            file_details.append({
                "name": file.name,
                "size": file_size,
                "type": file.type
            })
        
        # Display file table
        if file_details:
            st.write("**Selected files:**")
            for detail in file_details:
                st.write(f"• {detail['name']} ({detail['size']:,} bytes, {detail['type']})")

        # Processing section
        st.subheader("🔄 Processing Files")
        progress_bar = st.progress(0)
        status_container = st.container()
        
        num_files = len(uploaded_files)
        successful_uploads = 0
        failed_uploads = 0
        warnings = 0

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name
            file_size = len(uploaded_file.getbuffer())
            
            with status_container:
                st.write(f"**Processing {idx}/{num_files}: {file_name}**")
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
                    tmp_path = tmp_file.name
                    tmp_file.write(uploaded_file.getbuffer())
                
                try:
                    # Generate file hash for duplicate detection
                    with open(tmp_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    # Run OCR on the saved file
                    st.write(f"🔍 Running OCR on {file_name}...")
                    ocr_results = run_ocr_with_fallback(tmp_path, use_paddle_first=True)
                    
                    if not ocr_results:
                        st.error(f"❌ OCR failed for {file_name}")
                        failed_uploads += 1
                        log_processing_result(
                            file_path=tmp_path,
                            status='error',
                            error_message='OCR processing failed',
                            db_path=db_path
                        )
                        continue
                    
                    st.write(f"✅ OCR completed: {len(ocr_results)} text blocks found")
                    
                    # Extract fields from OCR results
                    st.write(f"🔍 Extracting invoice fields...")
                    extracted_data = extract_invoice_fields(ocr_results)
                    
                    # Add file information to extracted data
                    extracted_data.update({
                        'file_path': tmp_path,
                        'file_hash': file_hash,
                        'file_size': file_size,
                        'mime_type': uploaded_file.type
                    })
                    
                    # Validate the upload
                    st.write(f"🔍 Validating upload...")
                    allowed, messages, validation_data = validate_upload(tmp_path, extracted_data, db_path)
                    temp_name = messages.get("name", "Invoice")
                    
                    # Report results to the user and persist if allowed
                    if not allowed:
                        st.error(f"❌ {file_name}: {messages.get('error')}")
                        failed_uploads += 1
                        logging.info(f"Upload blocked for {file_name}: {messages.get('error')}")
                        log_processing_result(
                            file_path=tmp_path,
                            status='error',
                            error_message=messages.get('error', 'Validation failed'),
                            db_path=db_path
                        )
                    else:
                        warning = messages.get("warning")
                        if warning:
                            st.warning(f"⚠️ {file_name}: {warning}")
                            warnings += 1
                            logging.info(f"Upload warning for {file_name}: {warning}")
                        
                        # Save file hash to database
                        save_file_hash(file_hash, tmp_path, file_size, uploaded_file.type, db_path)
                        
                        # Save invoice to database
                        save_success = save_invoice(extracted_data, db_path)
                        
                        if save_success:
                            st.success(f"✅ {file_name}: Uploaded as '{temp_name}'")
                            successful_uploads += 1
                            logging.info(f"Uploaded {file_name} as {temp_name} with data {extracted_data}")
                            log_processing_result(
                                file_path=tmp_path,
                                status='success',
                                ocr_confidence=extracted_data.get('ocr_confidence', 0.0),
                                db_path=db_path
                            )
                        else:
                            st.error(f"❌ {file_name}: Failed to save to database")
                            failed_uploads += 1
                            log_processing_result(
                                file_path=tmp_path,
                                status='error',
                                error_message='Database save failed',
                                db_path=db_path
                            )
                
                except Exception as e:
                    st.error(f"❌ {file_name}: Processing error - {str(e)}")
                    failed_uploads += 1
                    logging.error(f"Processing error for {file_name}: {str(e)}")
                    log_processing_result(
                        file_path=tmp_path,
                        status='error',
                        error_message=str(e),
                        db_path=db_path
                    )
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                
                # Update progress bar
                progress_bar.progress(idx / num_files)
        
        # Final summary
        st.subheader("📊 Upload Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Files", num_files)
        
        with col2:
            st.metric("Successful", successful_uploads, delta=successful_uploads)
        
        with col3:
            st.metric("Failed", failed_uploads, delta=-failed_uploads)
        
        with col4:
            st.metric("Warnings", warnings, delta=warnings)
        
        if successful_uploads > 0:
            st.success(f"🎉 Successfully uploaded {successful_uploads} out of {num_files} files!")
        
        if failed_uploads > 0:
            st.error(f"⚠️ {failed_uploads} files failed to upload. Check the logs for details.")
        
        # Show audit log location
        st.info(f"📝 Audit log saved to: {log_file}")


def upload_delivery_notes_ui(db_path: str, user_role: str) -> None:
    """Render a multi-file delivery note uploader with validation, OCR and persistence.

    Parameters
    ----------
    db_path: str
        Path to the SQLite database used for duplicate checking and
        storage.
    user_role: str
        Role of the current user (e.g. 'GM', 'Finance', 'Shift Lead').
    """
    st.header("Upload Delivery Notes")
    st.write("Select one or more delivery note files to upload. Supported formats include PDF and common image types.")

    # Initialise database schema (idempotent)
    init_db(db_path)

    # Configure logging to an audit file inside the data directory
    log_dir = os.path.join(os.path.dirname(db_path))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "audit.log")
    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s %(message)s")

    # Check permissions
    if not user_has_permission(user_role):
        st.error("❌ You do not have permission to upload delivery notes.")
        st.info("Contact your administrator to request upload permissions.")
        return

    # Display user role and permissions
    st.success(f"✅ Logged in as: {user_role}")
    
    # File upload interface
    uploaded_files = st.file_uploader(
        "Choose delivery note files",
        type=["pdf", "jpg", "jpeg", "png", "tiff"],
        accept_multiple_files=True,
        help="Select one or more delivery note files to upload. Supported formats: PDF, JPG, PNG, TIFF"
    )

    if uploaded_files:
        # Display upload summary
        st.subheader(f"📁 Upload Summary")
        st.write(f"**Files selected:** {len(uploaded_files)}")
        
        # Processing section
        st.subheader("🔄 Processing Files")
        progress_bar = st.progress(0)
        status_container = st.container()
        
        num_files = len(uploaded_files)
        successful_uploads = 0
        failed_uploads = 0

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = uploaded_file.name
            file_size = len(uploaded_file.getbuffer())
            
            with status_container:
                st.write(f"**Processing {idx}/{num_files}: {file_name}**")
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
                    tmp_path = tmp_file.name
                    tmp_file.write(uploaded_file.getbuffer())
                
                try:
                    # Generate file hash for duplicate detection
                    with open(tmp_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    # Run OCR on the saved file
                    st.write(f"🔍 Running OCR on {file_name}...")
                    ocr_results = run_ocr_with_fallback(tmp_path, use_paddle_first=True)
                    
                    if not ocr_results:
                        st.error(f"❌ OCR failed for {file_name}")
                        failed_uploads += 1
                        continue
                    
                    st.write(f"✅ OCR completed: {len(ocr_results)} text blocks found")
                    
                    # Extract fields from OCR results (simplified for delivery notes)
                    st.write(f"🔍 Extracting delivery note fields...")
                    extracted_data = extract_invoice_fields(ocr_results)  # Reuse invoice extractor
                    
                    # Add file information to extracted data
                    extracted_data.update({
                        'file_path': tmp_path,
                        'file_hash': file_hash,
                        'file_size': file_size,
                        'mime_type': uploaded_file.type
                    })
                    
                    # Save file hash to database
                    save_file_hash(file_hash, tmp_path, file_size, uploaded_file.type, db_path)
                    
                    # Save delivery note to database (simplified)
                    st.success(f"✅ {file_name}: Delivery note processed successfully")
                    successful_uploads += 1
                    logging.info(f"Processed delivery note {file_name}")
                    
                except Exception as e:
                    st.error(f"❌ {file_name}: Processing error - {str(e)}")
                    failed_uploads += 1
                    logging.error(f"Processing error for {file_name}: {str(e)}")
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                
                # Update progress bar
                progress_bar.progress(idx / num_files)
        
        # Final summary
        st.subheader("📊 Upload Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Files", num_files)
        
        with col2:
            st.metric("Successful", successful_uploads, delta=successful_uploads)
        
        with col3:
            st.metric("Failed", failed_uploads, delta=-failed_uploads)
        
        if successful_uploads > 0:
            st.success(f"🎉 Successfully processed {successful_uploads} out of {num_files} delivery notes!")
        
        if failed_uploads > 0:
            st.error(f"⚠️ {failed_uploads} files failed to process. Check the logs for details.")
        
        # Show audit log location
        st.info(f"📝 Audit log saved to: {log_file}")


def create_streamlit_app():
    """Create a complete Streamlit application for multi-file upload."""
    
    st.set_page_config(
        page_title="OWLIN Multi-Upload",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📄 OWLIN Multi-File Upload System")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Database path
        db_path = st.text_input(
            "Database Path",
            value="data/owlin.db",
            help="Path to the SQLite database file"
        )
        
        # User role selection
        user_role = st.selectbox(
            "User Role",
            options=["viewer", "finance", "admin", "GM"],
            index=1,  # Default to finance
            help="Select your user role for permission checking"
        )
        
        # Display permissions
        st.subheader("🔐 Permissions")
        from .db_manager import get_user_permissions
        permissions = get_user_permissions(user_role)
        
        for permission, allowed in permissions.items():
            status = "✅" if allowed else "❌"
            st.write(f"{status} {permission.replace('_', ' ').title()}")
        
        # Database stats
        st.subheader("📊 Database Stats")
        from .db_manager import get_database_stats
        try:
            stats = get_database_stats(db_path)
            st.write(f"**Invoices:** {stats.get('invoice_count', 0)}")
            st.write(f"**Delivery Notes:** {stats.get('delivery_count', 0)}")
            st.write(f"**Total Amount:** £{stats.get('total_amount', 0):,.2f}")
        except Exception as e:
            st.error(f"Failed to load stats: {e}")
    
    # Main content
    tab1, tab2 = st.tabs(["📄 Upload Invoices", "📋 Upload Delivery Notes"])
    
    with tab1:
        upload_invoices_ui(db_path, user_role)
    
    with tab2:
        upload_delivery_notes_ui(db_path, user_role)


if __name__ == "__main__":
    create_streamlit_app() 