#!/usr/bin/env python3
"""
Script to fix all syntax errors in app/invoices_page.py
"""

import re

def fix_invoices_page():
    """Fix all syntax errors in the invoices page file."""
    
    # Read the file
    with open('app/invoices_page.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Remove duplicate function definitions
    # Find the second occurrence of sanitize_text and format_currency
    lines = content.split('\n')
    
    # Find duplicate function definitions
    sanitize_text_lines = []
    format_currency_lines = []
    
    for i, line in enumerate(lines):
        if line.strip().startswith('def sanitize_text('):
            sanitize_text_lines.append(i)
        elif line.strip().startswith('def format_currency('):
            format_currency_lines.append(i)
    
    # Remove the second occurrences (keep the first ones)
    if len(sanitize_text_lines) > 1:
        # Find the end of the second sanitize_text function
        start_line = sanitize_text_lines[1]
        end_line = start_line
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip().startswith('def ') and i > start_line:
                end_line = i - 1
                break
        # Remove the duplicate function
        lines = lines[:start_line] + lines[end_line + 1:]
    
    if len(format_currency_lines) > 1:
        # Find the end of the second format_currency function
        start_line = format_currency_lines[1]
        end_line = start_line
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip().startswith('def ') and i > start_line:
                end_line = i - 1
                break
        # Remove the duplicate function
        lines = lines[:start_line] + lines[end_line + 1:]
    
    # Fix 2: Fix all remaining f-string issues
    content = '\n'.join(lines)
    
    # Pattern to find problematic f-strings
    patterns = [
        # Pattern for multi-line f-strings with nested quotes
        (r'\{f\'\'\'\s*\n(.*?)\'\'\' if (.*?) else \'\'\'\s*\n(.*?)\'\'\'\}', 
         lambda m: f'{{{f"<div>{m.group(1).strip()}</div>" if m.group(2) else f"<div>{m.group(3).strip()}</div>"}}}'),
        
        # Pattern for single-line f-strings with nested quotes
        (r'\{f\'\'\'\s*(.*?)\'\'\' if (.*?) else \'\'\'\s*(.*?)\'\'\'\}', 
         lambda m: f'{{{f"<div>{m.group(1).strip()}</div>" if m.group(2) else f"<div>{m.group(3).strip()}</div>"}}}'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Fix 3: Replace problematic f-string patterns with simpler alternatives
    replacements = [
        # Replace complex f-strings with simpler conditional expressions
        (r'\{f\'\'\'\s*<div style="([^"]*)">([^<]*)</div>\s*\'\'\' if ([^}]+) else \'\'\'\s*<div style="([^"]*)">([^<]*)</div>\s*\'\'\'\}', 
         r'{f\'<div style="\1">\2</div>\' if \3 else \'<div style="\4">\5</div>\'}'),
        
        # Replace single-line f-strings with nested quotes
        (r'\{f\'\'\'\s*([^\']*)\'\'\' if ([^}]+) else \'\'\'\s*([^\']*)\'\'\'\}', 
         r'{f\'\1\' if \2 else \'\3\'}'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content back
    with open('app/invoices_page.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed invoices_page.py")
    print("Fixed issues:")
    print("- Removed duplicate function definitions")
    print("- Fixed f-string syntax errors")
    print("- Replaced problematic nested f-strings")

if __name__ == "__main__":
    fix_invoices_page() 