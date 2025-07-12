#!/usr/bin/env python3

def create_clean_invoices_file():
    """Create a clean version of invoices_page.py by removing duplicates and fixing syntax errors."""
    
    # Read the original file
    with open('app/invoices_page.py', 'r') as f:
        lines = f.readlines()
    
    # Find the problematic sections and create a clean version
    clean_lines = []
    in_problematic_section = False
    utility_functions_added = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip duplicate utility functions sections
        if '# --- Utility Functions ---' in line:
            if utility_functions_added:
                # Skip this duplicate section
                while i < len(lines) and not (lines[i].strip().startswith('def ') and 'render_' in lines[i]):
                    i += 1
                continue
            else:
                utility_functions_added = True
                clean_lines.append(line + '\n')
                # Add the correct utility functions
                clean_lines.extend([
                    'def get_enhanced_status_icon(status):\n',
                    '    """Get enhanced status icon HTML with better accessibility and visual feedback."""\n',
                    '    icons = {\n',
                    '        "matched": "✅",\n',
                    '        "discrepancy": "⚠️", \n',
                    '        "not_paired": "❌",\n',
                    '        "pending": "⏳",\n',
                    '        "processing": "🔄"\n',
                    '    }\n',
                    '    return icons.get(status, icons["pending"])\n',
                    '\n',
                    'def get_status_color(status):\n',
                    '    """Get color for status text."""\n',
                    '    colors = {\n',
                    '        "matched": "#4CAF50",\n',
                    '        "discrepancy": "#f1c232", \n',
                    '        "not_paired": "#ff3b30",\n',
                    '        "pending": "#888",\n',
                    '        "processing": "#007bff"\n',
                    '    }\n',
                    '    return colors.get(status, "#888")\n',
                    '\n',
                    'def get_status_counts(invoices):\n',
                    '    """Get counts of each status type."""\n',
                    '    counts = {\n',
                    '        "matched": 0,\n',
                    '        "discrepancy": 0,\n',
                    '        "not_paired": 0,\n',
                    '        "pending": 0,\n',
                    '        "processing": 0\n',
                    '    }\n',
                    '    for inv in invoices:\n',
                    '        status = inv.get("status", "pending")\n',
                    '        if status in counts:\n',
                    '            counts[status] += 1\n',
                    '    return counts\n',
                    '\n',
                    'def detect_status_changes(previous_invoices, current_invoices):\n',
                    '    """Detect status changes between previous and current invoice lists."""\n',
                    '    changes = []\n',
                    '    if not previous_invoices:\n',
                    '        return changes\n',
                    '    prev_lookup = {inv.get("id"): inv.get("status", "pending") for inv in previous_invoices}\n',
                    '    curr_lookup = {inv.get("id"): inv.get("status", "pending") for inv in current_invoices}\n',
                    '    for inv_id, current_status in curr_lookup.items():\n',
                    '        if inv_id in prev_lookup:\n',
                    '            previous_status = prev_lookup[inv_id]\n',
                    '            if previous_status != current_status:\n',
                    '                invoice_number = next((inv.get("invoice_number", "Unknown") for inv in current_invoices if inv.get("id") == inv_id), "Unknown")\n',
                    '                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")\n',
                    '    return changes\n',
                    '\n'
                ])
                i += 1
                continue
        
        # Handle the problematic refresh statuses section
        if '# Check if we need to refresh statuses' in line:
            # Add the correct refresh statuses section
            clean_lines.extend([
                '        # Check if we need to refresh statuses\n',
                '        time_since_last_check = (datetime.now() - st.session_state.last_status_check).total_seconds()\n',
                '        if time_since_last_check > 30:  # Refresh every 30 seconds\n',
                '            try:\n',
                '                # Reload invoices with fresh statuses\n',
                '                fresh_invoices = load_invoices_from_db()\n',
                '                if fresh_invoices:\n',
                '                    invoices = fresh_invoices\n',
                '                    st.session_state.last_status_check = datetime.now()\n',
                '                    \n',
                '                    # Announce status updates to screen readers\n',
                '                    status_changes = detect_status_changes(st.session_state.get("previous_invoices", []), invoices)\n',
                '                    if status_changes:\n',
                '                        for change in status_changes:\n',
                '                            announce_to_screen_reader(f"Status update: {change}", "polite")\n',
                '                \n',
                '                # Store current state for next comparison\n',
                '                st.session_state.previous_invoices = invoices.copy()\n',
                '                \n',
                '            except Exception as e:\n',
                '                st.warning(f"⚠️ Unable to refresh statuses: {str(e)}")\n',
                '\n'
            ])
            # Skip the problematic section
            while i < len(lines) and not ('# --- Utility Functions ---' in lines[i] or 'def render_' in lines[i]):
                i += 1
            continue
        
        # Skip duplicate function definitions
        if line.startswith('def ') and any(func in line for func in ['get_enhanced_status_icon', 'get_status_color', 'get_status_counts', 'detect_status_changes']):
            if utility_functions_added:
                # Skip this duplicate function
                while i < len(lines) and (lines[i].strip().startswith('def ') or lines[i].strip().startswith('    ') or lines[i].strip() == ''):
                    i += 1
                continue
        
        # Skip orphaned code blocks
        if any(orphaned in line for orphaned in ['changes.append(', 'status_changes = detect_status_changes', 'st.session_state.previous_invoices =']):
            if not in_problematic_section:
                # Skip this orphaned code
                while i < len(lines) and (lines[i].strip().startswith('    ') or lines[i].strip() == ''):
                    i += 1
                continue
        
        # Add the line if it's not problematic
        clean_lines.append(lines[i])
        i += 1
    
    # Write the clean file
    with open('app/invoices_page_clean.py', 'w') as f:
        f.writelines(clean_lines)
    
    print("Created clean invoices_page_clean.py")
    
    # Test the syntax
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', 'app/invoices_page_clean.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Syntax check passed!")
        # Replace the original file
        import shutil
        shutil.copy('app/invoices_page_clean.py', 'app/invoices_page.py')
        print("✅ Replaced original file with clean version")
    else:
        print("❌ Syntax check failed:")
        print(result.stderr)

if __name__ == "__main__":
    create_clean_invoices_file() 