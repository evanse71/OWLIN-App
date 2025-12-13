from fastapi import FastAPI
import httpx

app = FastAPI(title="Test App")

@app.on_event("startup")
async def startup():
    print("Startup event triggered")
    app.state.http = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown():
    print("Shutdown event triggered")
    if hasattr(app.state, "http"):
        await app.state.http.aclose()

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
