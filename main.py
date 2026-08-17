from fastapi import FastAPI
from routers import webhook_router

app = FastAPI(title="GitHub PR Review & ChatOps Bot")

app.include_router(webhook_router)


@app.get("/")
def health_check():
    return {"status": "active", "service": "GitHub PR Agent"}