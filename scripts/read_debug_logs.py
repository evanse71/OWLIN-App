import json
import os

log_path = '.cursor/debug.log'
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Get last 50 lines
    recent = lines[-50:] if len(lines) > 50 else lines
    
    # Filter for supplier-related logs
    for line in recent:
        if line.strip():
            try:
                data = json.loads(line)
                if 'supplier' in str(data.get('data', {})) or data.get('hypothesisId') == 'G':
                    print(f"{data.get('location')}: {data.get('message')}")
                    supplier = data.get('data', {}).get('supplier', 'N/A')
                    print(f"  Supplier: {supplier}")
                    print()
            except:
                pass
else:
    print("Debug log file not found")

