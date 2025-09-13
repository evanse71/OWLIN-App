from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import manual_entry

app = FastAPI(title="Owlin API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(manual_entry.router)

@app.get("/")
def read_root():
    return {"message": "Owlin API is running", "status": "OK"}

@app.get("/health")
def health():
    return {"status": "OK", "message": "Backend healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
