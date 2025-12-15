import requests
import os
import glob

# Find the latest '_Fresh_' PDF we created
list_of_files = glob.glob('data/uploads/*_Fresh_*.pdf')
if not list_of_files:
    print("❌ No Fresh PDF found! Run make_unique_invoice.py first.")
    exit()

latest_file = max(list_of_files, key=os.path.getctime)
print(f"🚀 Force Uploading: {latest_file}")

url = 'http://127.0.0.1:5176/api/ocr/process'
files = {'file': open(latest_file, 'rb')}

try:
    r = requests.post(url, files=files)
    print(f"✅ Status: {r.status_code}")
    print(r.json())
except Exception as e:
    print(f"❌ Error: {e}")
