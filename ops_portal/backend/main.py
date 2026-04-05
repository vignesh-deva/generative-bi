import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.tickets import router as tickets_router
from api.feedback import router as feedback_router
from api.rag import router as rag_router
from db.mongo import close_client, create_indexes
from db.database import get_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    await create_indexes()
    yield
    await close_pool()
    await close_client()


app = FastAPI(
    title="Generative BI — Operations Center API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router)
app.include_router(feedback_router)
app.include_router(rag_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
