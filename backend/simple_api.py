# backend/simple_api.py
from fastapi import APIRouter

# Create a simple API router without complex imports
simple_api = APIRouter()

@simple_api.get("/invoices")
def get_invoices():
    return {"message": "Invoices endpoint", "status": "working", "count": 0}

@simple_api.get("/suppliers") 
def get_suppliers():
    return {"message": "Suppliers endpoint", "status": "working", "count": 0}

@simple_api.get("/manual/invoices")
def get_manual_invoices():
    return {"message": "Manual invoices endpoint", "status": "working", "count": 0}

@simple_api.post("/manual/invoices")
def create_manual_invoice():
    return {"message": "Manual invoice created", "status": "working", "id": "test-123"}

# Add more endpoints as needed
