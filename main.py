from fastapi import FastAPI

app = FastAPI(title="Khushhal Backend", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Khushhal Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
