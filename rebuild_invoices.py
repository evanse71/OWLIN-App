#!/usr/bin/env python3

def rebuild_invoices_file():
    """Rebuild the invoices_page.py file from scratch with proper structure."""
    
    # Read the backup file
    with open('app/invoices_page_backup3.py', 'r') as f:
        content = f.read()
    
    # Find the problematic section and replace it with clean code
    start_marker = "# Check if we need to refresh statuses"
    end_marker = "# --- Utility Functions ---"
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print("Could not find markers in backup file")
        return
    
    # Extract parts before and after the problematic section
    before_section = content[:start_pos]
    after_section = content[end_pos:]
    
    # Create the clean replacement section
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
    
    # Create the rebuilt content
    rebuilt_content = before_section + replacement_section + after_section
    
    # Write the rebuilt file
    with open('app/invoices_page_rebuilt.py', 'w') as f:
        f.write(rebuilt_content)
    
    print("Created invoices_page_rebuilt.py")
    
    # Test the syntax
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', 'app/invoices_page_rebuilt.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Syntax check passed!")
        # Replace the original file
        import shutil
        shutil.copy('app/invoices_page_rebuilt.py', 'app/invoices_page.py')
        print("✅ Replaced original file with rebuilt version")
        return True
    else:
        print("❌ Syntax check failed:")
        print(result.stderr)
        return False

if __name__ == "__main__":
    rebuild_invoices_file() 