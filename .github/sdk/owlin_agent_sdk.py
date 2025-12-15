import requests
import pathlib

class OwlinAgentSDK:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip('/')
    
    def health(self):
        r = requests.get(f"{self.base_url}/api/health")
        r.raise_for_status()
        return r.json()
    
    def list_invoices(self):
        r = requests.get(f"{self.base_url}/api/invoices")
        r.raise_for_status()
        return r.json()
    
    def run_ocr(self, doc_id):
        r = requests.post(f"{self.base_url}/api/ocr/run", json={"doc_id": doc_id})
        r.raise_for_status()
        return r.json()
    
    def last_error(self):
        r = requests.get(f"{self.base_url}/api/debug/last_error")
        r.raise_for_status()
        return r.json()
    
    def upload(self, file_path: str) -> dict:
        """Upload a file and return doc_id"""
        p = pathlib.Path(file_path)
        with open(p, "rb") as f:
            r = requests.post(f"{self.base_url}/api/upload", files={"file": (p.name, f, "application/octet-stream")}, timeout=30)
        r.raise_for_status()
        return r.json()