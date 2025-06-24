from fastapi import FastAPI

from app.routers import webhook
from app.db import init_db

app = FastAPI(title="CodePing.AI WebhookReceiver")

@app.on_event("startup")
async def _on_startup() -> None:  # pragma: no cover
    await init_db()

app.include_router(webhook.router) 