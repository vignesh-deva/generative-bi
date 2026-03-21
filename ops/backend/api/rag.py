"""
RAG curation endpoint — ops team manages few-shot NL-to-SQL examples
stored in the PostgreSQL fewshot_examples table.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from db.database import execute_query, get_pool

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
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO fewshot_examples (question, sql_query, source) "
            "VALUES ($1, $2, 'curated') RETURNING example_id",
            body.question,
            body.sql,
        )
    return {"id": row["example_id"]}
