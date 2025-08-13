#!/usr/bin/env python3
"""
Comprehensive fix script for app/invoices_page.py
Fixes all syntax errors, duplicate functions, and undefined references.
"""

import re

def fix_invoices_page():
    """Fix all issues in the invoices page file."""
    
    print("🔧 Starting comprehensive fix of invoices_page.py...")
    
    # Read the file
    with open('app/invoices_page.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into lines for easier manipulation
    lines = content.split('\n')
    
    # Step 1: Remove duplicate function definitions
    print("📝 Step 1: Removing duplicate function definitions...")
    
    # Find all function definitions
    function_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith('def '):
            function_starts.append(i)
    
    # Find duplicates
    function_names = {}
    duplicates_to_remove = []
    
    for start_line in function_starts:
        func_name = lines[start_line].split('(')[0].replace('def ', '').strip()
        if func_name in function_names:
            # This is a duplicate
            duplicates_to_remove.append(start_line)
        else:
            function_names[func_name] = start_line
    
    # Remove duplicates (keep the first occurrence)
    for start_line in sorted(duplicates_to_remove, reverse=True):
        # Find the end of the function
        end_line = start_line
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip() == '':
                continue
            current_indent = len(lines[i]) - len(lines[i].lstrip())
            if current_indent <= indent_level and lines[i].strip().startswith('def '):
                break
            end_line = i
        
        # Remove the duplicate function
        lines = lines[:start_line] + lines[end_line + 1:]
        print(f"   Removed duplicate function at line {start_line}")
    
    # Step 2: Move utility functions to the top
    print("📝 Step 2: Moving utility functions to the top...")
    
    # Define the utility functions that need to be moved
    utility_functions = {
        'get_enhanced_status_icon': '''def get_enhanced_status_icon(status):
    """Get enhanced status icon HTML with better accessibility and visual feedback."""
    icons = {
        "matched": '<span class="owlin-invoice-status-icon owlin-invoice-status-matched" aria-label="Matched - Invoice and delivery note quantities match" title="Matched">✅</span>',
        "discrepancy": '<span class="owlin-invoice-status-icon owlin-invoice-status-discrepancy" aria-label="Discrepancy detected - Quantities don\\'t match" title="Discrepancy">⚠️</span>',
        "not_paired": '<span class="owlin-invoice-status-icon owlin-invoice-status-not_paired" aria-label="Not paired - Missing delivery note" title="Not Paired">❌</span>',
        "pending": '<span class="owlin-invoice-status-icon owlin-invoice-status-pending" aria-label="Pending - Awaiting processing" title="Pending">⏳</span>',
        "processing": '<span class="owlin-invoice-status-icon owlin-invoice-status-processing" aria-label="Processing - Currently being analyzed" title="Processing">🔄</span>'
    }
    return icons.get(status, icons["pending"])''',
        
        'get_status_color': '''def get_status_color(status):
    """Get color for status text."""
    colors = {
        "matched": "#4CAF50",
        "discrepancy": "#f1c232", 
        "not_paired": "#ff3b30",
        "pending": "#888",
        "processing": "#007bff"
    }
    return colors.get(status, "#888")''',
        
        'get_status_counts': '''def get_status_counts(invoices):
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
    
    return counts''',
        
        'detect_status_changes': '''def detect_status_changes(previous_invoices, current_invoices):
    """Detect status changes between previous and current invoice lists."""
    changes = []
    
    if not previous_invoices:
        return changes
    
    # Create lookup dictionaries
    prev_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in previous_invoices}
    curr_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in current_invoices}
    
    # Check for status changes
    for inv_id, current_status in curr_lookup.items():
        if inv_id in prev_lookup:
            previous_status = prev_lookup[inv_id]
            if previous_status != current_status:
                invoice_number = next((inv.get('invoice_number', 'Unknown') for inv in current_invoices if inv.get('id') == inv_id), 'Unknown')
                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")
    
    return changes'''
    }
    
    # Find where to insert the utility functions (before the first use)
    insert_line = None
    for i, line in enumerate(lines):
        if any(func_name in line for func_name in utility_functions.keys()):
            insert_line = i
            break
    
    if insert_line is None:
        insert_line = 750  # Default position after imports and initial functions
    
    # Insert utility functions
    utility_code = '\n\n# --- Utility Functions ---\n' + '\n\n'.join(utility_functions.values())
    lines.insert(insert_line, utility_code)
    
    # Step 3: Fix f-string issues
    print("📝 Step 3: Fixing f-string issues...")
    
    content = '\n'.join(lines)
    
    # Fix problematic f-string patterns
    patterns_to_fix = [
        # Pattern 1: Multi-line f-strings with nested quotes
        (r'\{f\'\'\'\s*\n(.*?)\'\'\' if (.*?) else \'\'\'\s*\n(.*?)\'\'\'\}', 
         lambda m: f'{{{f"<div>{m.group(1).strip()}</div>" if m.group(2) else f"<div>{m.group(3).strip()}</div>"}}}'),
        
        # Pattern 2: Single-line f-strings with nested quotes
        (r'\{f\'\'\'\s*(.*?)\'\'\' if ([^}]+) else \'\'\'\s*(.*?)\'\'\'\}', 
         lambda m: f'{{{f"<div>{m.group(1).strip()}</div>" if m.group(2) else f"<div>{m.group(3).strip()}</div>"}}}'),
        
        # Pattern 3: Complex HTML in f-strings
        (r'\{f\'\'\'\s*<div style="([^"]*)">([^<]*)</div>\s*\'\'\' if ([^}]+) else \'\'\'\s*<div style="([^"]*)">([^<]*)</div>\s*\'\'\'\}', 
         r'{f\'<div style="\1">\2</div>\' if \3 else \'<div style="\4">\5</div>\'}'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Step 4: Clean up any remaining issues
    print("📝 Step 4: Cleaning up remaining issues...")
    
    # Remove any duplicate lines that might have been created
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        if line not in cleaned_lines or not line.strip().startswith('issues_detected_error_count'):
            cleaned_lines.append(line)
    
    # Write the fixed content back
    with open('app/invoices_page.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned_lines))
    
    print("✅ Comprehensive fix completed!")
    print("Fixed issues:")
    print("- Removed duplicate function definitions")
    print("- Moved utility functions to the top")
    print("- Fixed f-string syntax errors")
    print("- Cleaned up duplicate lines")

if __name__ == "__main__":
    fix_invoices_page() 