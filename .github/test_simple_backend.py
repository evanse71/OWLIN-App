#!/usr/bin/env python3
"""
Simple test backend for Owlin
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Owlin Test API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/invoices")
def invoices():
    return {"invoices": []}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
