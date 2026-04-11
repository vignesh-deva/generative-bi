"""
RAG curation endpoint — ops team manages few-shot NL-to-SQL examples
stored in the PostgreSQL fewshot_examples table.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import execute_query, get_pool
from tools.embedding import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


class FewshotCreate(BaseModel):
    question: str
    sql: str


@router.get("/fewshots")
async def list_fewshots(limit: int = 100, skip: int = 0):
    result = await execute_query(
        "SELECT example_id, question, sql_query, created_at FROM fewshot_examples "
        "ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        [limit, skip],
    )
    return [
        {
            "id": row[0],
            "question": row[1],
            "sql": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
        }
        for row in result["rows"]
    ]


@router.post("/fewshots")
async def create_fewshot(body: FewshotCreate):
    question = body.question.strip()
    sql = body.sql.strip()
    if not question or not sql:
        raise HTTPException(
            status_code=400, detail="question and sql must be non-empty"
        )

    try:
        embedding = await get_embedding(question)
    except Exception as e:
        # Keep the manual curation path usable even if the embedding service
        # is down — insert with NULL embedding and log the degradation.
        logger.warning("embedding unavailable on manual insert: %s", e)
        embedding = None

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO fewshot_examples (question, sql_query, embedding, source) "
            "VALUES ($1, $2, $3, 'curated') RETURNING example_id",
            question,
            sql,
            embedding,
        )
    return {"id": row["example_id"]}
