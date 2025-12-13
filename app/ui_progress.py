"""
UI Progress Feedback Module for Owlin App
Handles real-time progress updates, status indicators, and error reporting.

Usage:
    from app.ui_progress import ProgressTracker, show_processing_status
    tracker = ProgressTracker()
    tracker.update_status("Processing file...", 25)
"""
import streamlit as st
import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks and displays processing progress with real-time updates."""
    
    def __init__(self, session_key: str = "processing_progress"):
        self.session_key = session_key
        self.start_time = None
        self.current_step = ""
        self.progress = 0
        self.status = "idle"
        self.error_message = ""
        self.warnings = []
        self.details = {}
        
        # Initialize session state
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {
                'status': 'idle',
                'progress': 0,
                'current_step': '',
                'error_message': '',
                'warnings': [],
                'details': {},
                'start_time': None,
                'last_update': None
            }
    
    def start_processing(self, total_files: int = 1):
        """Start a new processing session."""
        self.start_time = datetime.now()
        self.status = "processing"
        self.progress = 0
        self.current_step = "Initializing..."
        self.error_message = ""
        self.warnings = []
        self.details = {
            'total_files': total_files,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'created_invoices': 0
        }
        
        self._update_session_state()
        logger.info(f"Started processing session for {total_files} files")
    
    def update_status(self, step: str, progress: int, details: Optional[Dict] = None):
        """Update current processing status."""
        self.current_step = step
        self.progress = max(0, min(100, progress))
        
        if details:
            self.details.update(details)
        
        self._update_session_state()
        logger.debug(f"Progress update: {step} ({progress}%)")
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append({
            'message': warning,
            'timestamp': datetime.now().isoformat()
        })
        self._update_session_state()
        logger.warning(f"Processing warning: {warning}")
    
    def set_error(self, error: str):
        """Set an error message and mark processing as failed."""
        self.error_message = error
        self.status = "failed"
        self._update_session_state()
        logger.error(f"Processing error: {error}")
    
    def complete_processing(self, results: Dict):
        """Mark processing as completed with results."""
        self.status = "completed"
        self.progress = 100
        self.current_step = "Processing completed"
        self.details.update(results)
        self._update_session_state()
        logger.info(f"Processing completed: {results}")
    
    def _update_session_state(self):
        """Update the session state with current progress."""
        st.session_state[self.session_key] = {
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'warnings': self.warnings,
            'details': self.details,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': datetime.now().isoformat()
        }
    
    def get_elapsed_time(self) -> str:
        """Get elapsed time as a formatted string."""
        if not self.start_time:
            return "0s"
        
        elapsed = datetime.now() - self.start_time
        if elapsed.total_seconds() < 60:
            return f"{int(elapsed.total_seconds())}s"
        elif elapsed.total_seconds() < 3600:
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"

def show_processing_status(tracker: ProgressTracker, container=None):
    """Display processing status with progress bar and details."""
    if container is None:
        container = st.container()
    
    with container:
        # Get current state
        state = st.session_state.get(tracker.session_key, {})
        status = state.get('status', 'idle')
        progress = state.get('progress', 0)
        current_step = state.get('current_step', '')
        error_message = state.get('error_message', '')
        warnings = state.get('warnings', [])
        details = state.get('details', {})
        
        # Status indicator
        if status == "processing":
            st.markdown("🔄 **Processing Files...**")
        elif status == "completed":
            st.markdown("✅ **Processing Completed**")
        elif status == "failed":
            st.markdown("❌ **Processing Failed**")
        else:
            st.markdown("⏸️ **Ready to Process**")
        
        # Progress bar
        if status in ["processing", "completed"]:
            st.progress(progress / 100)
        
        # Current step
        if current_step:
            st.markdown(f"**Current Step:** {current_step}")
        
        # Elapsed time
        if status == "processing":
            elapsed = tracker.get_elapsed_time()
            st.markdown(f"**Elapsed Time:** {elapsed}")
        
        # Error message
        if error_message:
            st.error(f"**Error:** {error_message}")
        
        # Warnings
        if warnings:
            with st.expander(f"⚠️ Warnings ({len(warnings)})", expanded=False):
                for warning in warnings[-5:]:  # Show last 5 warnings
                    st.warning(warning['message'])
        
        # Processing details
        if details:
            with st.expander("📊 Processing Details", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Files", details.get('total_files', 0))
                
                with col2:
                    st.metric("Successful", details.get('successful_files', 0))
                
                with col3:
                    st.metric("Failed", details.get('failed_files', 0))
                
                if details.get('created_invoices', 0) > 0:
                    st.success(f"✅ Created {details.get('created_invoices', 0)} invoice records")

def show_file_upload_status(file_key: str, container=None):
    """Display individual file upload status."""
    if container is None:
        container = st.container()
    
    with container:
        upload_status = st.session_state.get(f'{file_key}_upload_status', {})
        
        if not upload_status:
            return
        
        for file_key, status in upload_status.items():
            if status.get('status') == 'processing':
                st.info(f"🔄 {status.get('message', 'Processing...')}")
                if status.get('progress', 0) > 0:
                    st.progress(status.get('progress', 0) / 100)
            elif status.get('status') == 'success':
                st.success(f"✅ {status.get('message', 'Completed')}")
            elif status.get('status') == 'warning':
                st.warning(f"⚠️ {status.get('message', 'Warning')}")
            elif status.get('status') == 'error':
                st.error(f"❌ {status.get('message', 'Error')}")

def create_processing_callback(tracker: ProgressTracker) -> Callable:
    """Create a callback function for processing updates."""
    def callback(step: str, progress: int, details: Optional[Dict] = None):
        tracker.update_status(step, progress, details)
        time.sleep(0.1)  # Small delay to allow UI updates
    
    return callback

def show_debug_info(container=None):
    """Display debug information for troubleshooting."""
    if container is None:
        container = st.container()
    
    with container:
        with st.expander("🐛 Debug Information", expanded=False):
            # Database connection status
            try:
                from app.database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM uploaded_files")
                file_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM invoices")
                invoice_count = cursor.fetchone()[0]
                conn.close()
                
                st.markdown(f"**Database Status:** ✅ Connected")
                st.markdown(f"**Uploaded Files:** {file_count}")
                st.markdown(f"**Invoices:** {invoice_count}")
            except Exception as e:
                st.error(f"**Database Error:** {e}")
            
            # OCR availability
            try:
                from app.ocr_factory import get_ocr_recognizer
                recognizer = get_ocr_recognizer()
                st.markdown(f"**OCR Engine:** {type(recognizer).__name__}")
                st.markdown(f"**OCR Available:** {'✅ Yes' if recognizer.available else '❌ No'}")
            except Exception as e:
                st.error(f"**OCR Error:** {e}")
            
            # Session state info
            st.markdown("**Session State Keys:**")
            for key in st.session_state.keys():
                if 'upload' in key or 'processing' in key:
                    st.markdown(f"- {key}")

def announce_to_screen_reader(message: str, priority: str = 'polite'):
    """Announce message to screen readers."""
    # This would integrate with actual screen reader APIs
    # For now, we'll use Streamlit's built-in accessibility features
    st.markdown(f'<div aria-live="{priority}" class="sr-only">{message}</div>', unsafe_allow_html=True) 