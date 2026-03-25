"""
RAG tools — retrieve few-shot NL-to-SQL examples via pgvector cosine similarity.

Tools:
  retrieve_fewshots(query_embedding, limit)  — vector search on fewshot_examples
  get_embedding(text)  — generate embedding via the configured embedding model
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, EMBEDDING_MODEL
from db.database import get_pool

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


async def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def retrieve_fewshots(
    query: str, limit: int = 5
) -> list[dict]:
    """Retrieve few-shot examples by cosine similarity. Returns list of
    {question, sql, similarity} dicts, ordered by similarity descending."""
    try:
        embedding = await get_embedding(query)
    except Exception:
        # Fallback: return recent examples if embedding fails
        return await _fallback_recent(limit)

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT question, sql_query, "
            "1 - (embedding <=> $1::vector) AS similarity "
            "FROM fewshot_examples "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> $1::vector "
            "LIMIT $2",
            str(embedding), limit,
        )

    if not rows:
        return await _fallback_recent(limit)

    return [
        {
            "question": row["question"],
            "sql": row["sql_query"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]


async def _fallback_recent(limit: int) -> list[dict]:
    """Fallback: return most recent examples without vector search."""
    from db.database import execute_query

    try:
        result = await execute_query(
            "SELECT question, sql_query FROM fewshot_examples "
            "ORDER BY created_at DESC LIMIT $1",
            [limit],
        )
        return [
            {"question": row[0], "sql": row[1], "similarity": 0.0}
            for row in result["rows"]
        ]
    except Exception:
        return []
