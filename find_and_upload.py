import requests
import os
import glob

# Find the file
list_of_files = glob.glob('data/uploads/*_Fresh_*.pdf')
if not list_of_files:
    print("❌ No Fresh PDF found!")
    exit()
latest_file = max(list_of_files, key=os.path.getctime)

# --- TRY MULTIPLE ENDPOINTS ---
urls_to_try = [
    'http://127.0.0.1:5176/api/upload',          # Common
    'http://127.0.0.1:5176/api/invoices/upload', # Semantic
    'http://127.0.0.1:5176/api/ocr/process',     # Previous guess
    'http://127.0.0.1:5176/upload'               # Root
]

print(f"🚀 Trying to upload: {latest_file}")
file_content = open(latest_file, 'rb').read()

for url in urls_to_try:
    print(f"\nTesting URL: {url}")
    try:
        # Re-open file for each attempt
        files = {'file': (os.path.basename(latest_file), file_content, 'application/pdf')}
        r = requests.post(url, files=files)
        
        if r.status_code == 200:
            print(f"✅ SUCCESS! Found the door: {url}")
            print(r.json())
            break
        else:
            print(f"❌ {r.status_code}: {r.text[:50]}...")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

