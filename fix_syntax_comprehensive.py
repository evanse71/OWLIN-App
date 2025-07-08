#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_syntax_comprehensive():
    """Comprehensive fix for all syntax errors in invoices_page.py."""
    
    # Read the backup file
    with open('app/invoices_page_backup3.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add UTF-8 encoding declaration
    if not content.startswith('# -*- coding: utf-8 -*-'):
        content = '# -*- coding: utf-8 -*-\n' + content
    
    # Find and fix the problematic section
    start_marker = "# Check if we need to refresh statuses"
    end_marker = "# --- Component: Upload Box ---"
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print("Could not find markers in backup file")
        return False
    
    # Extract parts before and after the problematic section
    before_section = content[:start_pos]
    after_section = content[end_pos:]
    
    # Create clean replacement section with proper function definitions
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

# --- Component: Upload Box ---
'''
    
    # Create the fixed content
    fixed_content = before_section + replacement_section + after_section
    
    # Remove any remaining malformed code blocks
    lines = fixed_content.split('\n')
    cleaned_lines = []
    skip_until_indent = 0
    
    for i, line in enumerate(lines):
        # Skip malformed code blocks
        if skip_until_indent > 0:
            if line.strip() and len(line) - len(line.lstrip()) <= skip_until_indent:
                skip_until_indent = 0
            else:
                continue
        
        # Check for malformed function content
        if '                invoice_number = next(' in line and 'changes.append(' in line:
            # This is malformed code, skip until proper indentation
            skip_until_indent = len(line) - len(line.lstrip())
            continue
        
        # Check for other malformed patterns
        if '                    status_changes = detect_status_changes(' in line:
            skip_until_indent = len(line) - len(line.lstrip())
            continue
        
        cleaned_lines.append(line)
    
    fixed_content = '\n'.join(cleaned_lines)
    
    # Write the fixed file
    with open('app/invoices_page_fixed3.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Created invoices_page_fixed3.py")
    
    # Test the syntax
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', 'app/invoices_page_fixed3.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Syntax check passed!")
        # Replace the original file
        import shutil
        shutil.copy('app/invoices_page_fixed3.py', 'app/invoices_page.py')
        print("✅ Replaced original file with fixed version")
        return True
    else:
        print("❌ Syntax check failed:")
        print(result.stderr)
        return False

if __name__ == "__main__":
    print("🔧 Comprehensive syntax fix...")
    
    if fix_syntax_comprehensive():
        print("✅ Syntax errors fixed successfully!")
    else:
        print("❌ Failed to fix syntax errors") 