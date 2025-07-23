#!/usr/bin/env python3
"""
Fix the format_currency function indentation in invoices_page.py
"""

def fix_format_currency():
    """Fix the format_currency function indentation."""
    
    # Read the file
    with open('app/invoices_page.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the format_currency function and fix it
    fixed_lines = []
    in_format_currency = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if we're entering the format_currency function
        if line.strip().startswith('def format_currency('):
            in_format_currency = True
            fixed_lines.append(line)
            i += 1
            continue
        
        # If we're in the format_currency function, fix indentation
        if in_format_currency:
            if line.strip() == '':
                fixed_lines.append(line)
                i += 1
                continue
            
            if line.strip().startswith('"""') or line.strip().endswith('"""'):
                # Docstring lines
                fixed_lines.append(line)
                i += 1
                continue
            
            if line.strip().startswith('try:'):
                fixed_lines.append('    try:\n')
                i += 1
                continue
            
            if line.strip().startswith('if amount is None:'):
                fixed_lines.append('        if amount is None:\n')
                i += 1
                continue
            
            if line.strip().startswith('return \'£0.00\''):
                fixed_lines.append('            return \'£0.00\'\n')
                i += 1
                continue
            
            if line.strip().startswith('# Convert to float'):
                fixed_lines.append('        # Convert to float and handle edge cases\n')
                i += 1
                continue
            
            if line.strip().startswith('amount = float(amount)'):
                fixed_lines.append('        amount = float(amount)\n')
                i += 1
                continue
            
            if line.strip().startswith('if amount < 0:'):
                fixed_lines.append('        if amount < 0:\n')
                i += 1
                continue
            
            if line.strip().startswith('return f\'-£{abs(amount):,.2f}\''):
                fixed_lines.append('            return f\'-£{abs(amount):,.2f}\'\n')
                i += 1
                continue
            
            if line.strip().startswith('else:'):
                fixed_lines.append('        else:\n')
                i += 1
                continue
            
            if line.strip().startswith('return f\'£{amount:,.2f}\''):
                fixed_lines.append('            return f\'£{amount:,.2f}\'\n')
                i += 1
                continue
            
            if line.strip().startswith('except (ValueError, TypeError):'):
                fixed_lines.append('    except (ValueError, TypeError):\n')
                i += 1
                continue
            
            if line.strip().startswith('return \'£0.00\''):
                fixed_lines.append('        return \'£0.00\'\n')
                i += 1
                continue
            
            # Check if we're exiting the function
            if line.strip() == '' and i + 1 < len(lines) and not lines[i + 1].startswith('    '):
                in_format_currency = False
                fixed_lines.append(line)
                i += 1
                continue
            
            # Skip any other lines in the function that have wrong indentation
            i += 1
            continue
        
        # Normal line processing
        fixed_lines.append(line)
        i += 1
    
    # Write the fixed file
    with open('app/invoices_page.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("Fixed format_currency function indentation")

if __name__ == "__main__":
    fix_format_currency() 