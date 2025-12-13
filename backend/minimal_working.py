from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Minimal Working")

@app.get("/")
def root():
    return {"message": "Hello World", "status": "running"}

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/status")
def status():
    return {"ok": True, "message": "Minimal API working"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
