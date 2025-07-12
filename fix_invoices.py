#!/usr/bin/env python3

def fix_invoices_file():
    """Fix the invoices_page.py file by replacing the problematic utility functions section."""
    
    # Read the original file
    with open('app/invoices_page.py', 'r') as f:
        lines = f.readlines()
    
    # Find the utility functions section
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if '# --- Utility Functions ---' in line:
            start_line = i
            break
    
    if start_line is None:
        print("Could not find utility functions section")
        return
    
    # Find where the utility functions section ends (look for the next function or main code)
    for i in range(start_line + 1, len(lines)):
        line = lines[i].strip()
        if line.startswith('def ') and 'render_' in line:
            end_line = i
            break
        elif line.startswith('status_changes = ') or line.startswith('st.markdown('):
            end_line = i
            break
    
    if end_line is None:
        end_line = start_line + 1
    
    # Create the correct utility functions
    utility_functions = '''def get_enhanced_status_icon(status):
    """Get enhanced status icon HTML with better accessibility and visual feedback."""
    icons = {
        "matched": '<span class="owlin-invoice-status-icon owlin-invoice-status-matched" aria-label="Matched - Invoice and delivery note quantities match" title="Matched">✅</span>',
        "discrepancy": '<span class="owlin-invoice-status-icon owlin-invoice-status-discrepancy" aria-label="Discrepancy detected - Quantities don\\'t match" title="Discrepancy">⚠️</span>',
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
    
    # Replace the problematic section
    new_lines = lines[:start_line + 1] + [utility_functions] + lines[end_line:]
    
    # Write the fixed file
    with open('app/invoices_page.py', 'w') as f:
        f.writelines(new_lines)
    
    print(f"Fixed invoices_page.py: replaced lines {start_line}-{end_line}")

if __name__ == "__main__":
    fix_invoices_file() 