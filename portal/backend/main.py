import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dashboard import router as dashboard_router
from api.chat import router as chat_router
from api.history import router as history_router
from api.requests import router as requests_router
from db.database import get_pool, close_pool
from db.mongo import close_client, create_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    await create_indexes()
    yield
    await close_pool()
    await close_client()


app = FastAPI(
    title="Generative BI Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(requests_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
