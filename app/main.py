from fastapi import FastAPI

from app.routers import webhook

app = FastAPI(title="CodePing.AI WebhookReceiver")

app.include_router(webhook.router) 