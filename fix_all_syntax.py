#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_all_syntax_errors():
    """Fix all syntax errors in invoices_page.py and related files."""
    
    # Read the original backup file
    with open('app/invoices_page_backup3.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add UTF-8 encoding declaration at the top
    if not content.startswith('# -*- coding: utf-8 -*-'):
        content = '# -*- coding: utf-8 -*-\n' + content
    
    # Find and fix the problematic section
    start_marker = "# Check if we need to refresh statuses"
    end_marker = "# --- Utility Functions ---"
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print("Could not find markers in backup file")
        return False
    
    # Extract parts before and after the problematic section
    before_section = content[:start_pos]
    after_section = content[end_pos:]
    
    # Create the clean replacement section with proper syntax
    replacement_section = '''        # Check if we need to refresh statuses
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
'''
    
    # Create the fixed content
    fixed_content = before_section + replacement_section + after_section
    
    # Write the fixed file
    with open('app/invoices_page_fixed.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Created invoices_page_fixed.py")
    
    # Test the syntax
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', 'app/invoices_page_fixed.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Syntax check passed!")
        # Replace the original file
        import shutil
        shutil.copy('app/invoices_page_fixed.py', 'app/invoices_page.py')
        print("✅ Replaced original file with fixed version")
        return True
    else:
        print("❌ Syntax check failed:")
        print(result.stderr)
        return False

def clean_up_backup_files():
    """Remove or archive outdated invoice page modules."""
    import os
    import shutil
    from datetime import datetime
    
    # Create archive directory
    archive_dir = f"backup_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(archive_dir, exist_ok=True)
    
    # Files to archive
    backup_files = [
        'app/invoices_page_backup.py',
        'app/invoices_page_backup2.py', 
        'app/invoices_page_backup3.py',
        'app/invoices_page_clean.py',
        'app/invoices_page_rebuilt.py',
        'app/invoices_page_fresh.py',
        'app/temp_invoices_page.py',
        'app/invoices_page_fixed.py'
    ]
    
    moved_files = []
    for file_path in backup_files:
        if os.path.exists(file_path):
            try:
                shutil.move(file_path, os.path.join(archive_dir, os.path.basename(file_path)))
                moved_files.append(file_path)
                print(f"📦 Archived: {file_path}")
            except Exception as e:
                print(f"❌ Failed to archive {file_path}: {e}")
    
    print(f"✅ Archived {len(moved_files)} backup files to {archive_dir}/")
    return archive_dir

def add_utf8_headers():
    """Add UTF-8 encoding headers to files containing Unicode."""
    import os
    
    # Files that likely contain Unicode/emoji
    unicode_files = [
        'app/invoices_page.py',
        'app/main.py',
        'app/file_processor.py',
        'app/database.py'
    ]
    
    for file_path in unicode_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add UTF-8 header if not present
                if not content.startswith('# -*- coding: utf-8 -*-'):
                    content = '# -*- coding: utf-8 -*-\n' + content
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Added UTF-8 header to: {file_path}")
                else:
                    print(f"ℹ️  UTF-8 header already present in: {file_path}")
                    
            except Exception as e:
                print(f"❌ Failed to add UTF-8 header to {file_path}: {e}")

if __name__ == "__main__":
    print("🔧 Fixing all syntax errors and cleaning up...")
    
    # Fix syntax errors
    if fix_all_syntax_errors():
        print("✅ Syntax errors fixed successfully!")
        
        # Clean up backup files
        archive_dir = clean_up_backup_files()
        
        # Add UTF-8 headers
        add_utf8_headers()
        
        print("\n🎉 All issues resolved!")
        print(f"📦 Backup files archived to: {archive_dir}/")
        print("✅ UTF-8 headers added to Unicode files")
        print("✅ invoices_page.py is now syntax-error-free")
    else:
        print("❌ Failed to fix syntax errors") 