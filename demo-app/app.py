import os

from fastapi import FastAPI, Response

app = FastAPI(title="demo-api")

VERSION = os.getenv("APP_VERSION", "dev")
BROKEN = os.getenv("BROKEN", "false").lower() == "true"


@app.get("/")
def home():
    return {"service": "demo-api", "version": VERSION}


@app.get("/health")
def health(response: Response):
    if BROKEN:
        response.status_code = 500
        return {"status": "unhealthy", "version": VERSION}
    return {"status": "ok", "version": VERSION}