#!/usr/bin/env python3
"""
Fix indentation errors in invoices_page.py by removing orphaned indented lines.
"""

def fix_indentation_errors():
    """Fix the indentation errors in the invoices_page.py file."""
    
    # Read the file
    with open('app/invoices_page.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Lines to remove (orphaned indented lines)
    lines_to_remove = [
        '                invoice_number = next((inv.get(\'invoice_number\', \'Unknown\') for inv in current_invoices if inv.get(\'id\') == inv_id), \'Unknown\')\n',
        '                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")\n',
        '    return changes\n',
        '                    status_changes = detect_status_changes(st.session_state.get(\'previous_invoices\', []), invoices)\n',
        '                    if status_changes:\n',
        '                        for change in status_changes:\n',
        '                            announce_to_screen_reader(f"Status update: {change}", \'polite\')\n',
        '                \n',
        '                # Store current state for next comparison\n',
        '                st.session_state.previous_invoices = invoices.copy()\n',
        '                \n',
        '            except Exception as e:\n',
        '                st.warning(f"⚠️ Unable to refresh statuses: {str(e)}")\n'
    ]
    
    # Remove the orphaned lines
    fixed_lines = []
    for line in lines:
        if line not in lines_to_remove:
            fixed_lines.append(line)
    
    # Write the fixed file
    with open('app/invoices_page.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("Fixed indentation errors in invoices_page.py")

if __name__ == "__main__":
    fix_indentation_errors() 