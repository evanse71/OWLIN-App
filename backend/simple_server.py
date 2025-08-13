#!/usr/bin/env python3
"""
Simple FastAPI server for testing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Owlin Simple API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Owlin API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Backend server is running"}

@app.get("/api/health")
def api_health_check():
    return {"status": "healthy", "message": "API endpoint is working"}

if __name__ == "__main__":
    print("🚀 Starting simple Owlin backend server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("✅ Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000) 