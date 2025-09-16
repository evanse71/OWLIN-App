import uvicorn
def main():
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=False, workers=1, log_level="info")
if __name__ == "__main__":
    main()
