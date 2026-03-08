"""FastAPI application entry point for the Support Copilot API."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.routers import chat, suggest, feedback, upload

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

app = FastAPI(
    title="Support Copilot API",
    version="0.1.0",
    root_path=os.getenv("ROOT_PATH", ""),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins=["*"]; we use X-API-Key, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(suggest.router)
app.include_router(feedback.router)
app.include_router(upload.router)


@app.get("/health")
async def health():
    version = os.getenv("APP_VERSION", "dev")
    return {"status": "ok", "version": version}
