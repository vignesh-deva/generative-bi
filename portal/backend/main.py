from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@app.get("/health")
async def health():
    return {"status": "ok"}
