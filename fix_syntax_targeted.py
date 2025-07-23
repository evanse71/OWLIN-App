#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_syntax_errors_targeted():
    """Fix syntax errors by removing duplicates and fixing malformed sections."""
    
    # Read the backup file
    with open('app/invoices_page_backup3.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add UTF-8 encoding declaration
    if not content.startswith('# -*- coding: utf-8 -*-'):
        content = '# -*- coding: utf-8 -*-\n' + content
    
    # Find the problematic section and replace it completely
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
    
    # Create clean replacement section
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

# --- Component: Upload Box ---
'''
    
    # Create the fixed content
    fixed_content = before_section + replacement_section + after_section
    
    # Remove duplicate function definitions
    lines = fixed_content.split('\n')
    cleaned_lines = []
    seen_functions = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a function definition
        if line.startswith('def ') and '(' in line:
            func_name = line.split('(')[0].replace('def ', '').strip()
            
            if func_name in seen_functions:
                # Skip this function and find its end
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                i += 1
                while i < len(lines):
                    if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= indent_level:
                        break
                    i += 1
                continue
            else:
                seen_functions.add(func_name)
        
        cleaned_lines.append(lines[i])
        i += 1
    
    fixed_content = '\n'.join(cleaned_lines)
    
    # Write the fixed file
    with open('app/invoices_page_fixed2.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Created invoices_page_fixed2.py")
    
    # Test the syntax
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', 'app/invoices_page_fixed2.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Syntax check passed!")
        # Replace the original file
        import shutil
        shutil.copy('app/invoices_page_fixed2.py', 'app/invoices_page.py')
        print("✅ Replaced original file with fixed version")
        return True
    else:
        print("❌ Syntax check failed:")
        print(result.stderr)
        return False

if __name__ == "__main__":
    print("🔧 Fixing syntax errors with targeted approach...")
    
    if fix_syntax_errors_targeted():
        print("✅ Syntax errors fixed successfully!")
    else:
        print("❌ Failed to fix syntax errors") 