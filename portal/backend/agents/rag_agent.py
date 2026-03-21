"""
RAG agent — retrieves few-shot NL-to-SQL examples from the pgvector store.

Returns a list of {question, sql} dicts for use as few-shot context.

NOTE: Full vector search requires an embedding model. For now, this falls
back to returning recent examples until the embedding model is configured.
"""

from db.database import execute_query


async def retrieve_fewshots(query: str, limit: int = 5) -> list[dict]:
    # TODO: Once embedding model is chosen, generate query embedding
    # and use vector similarity search:
    #   SELECT question, sql_query
    #   FROM fewshot_examples
    #   ORDER BY embedding <=> $1::vector
    #   LIMIT $2

    try:
        result = await execute_query(
            "SELECT question, sql_query FROM fewshot_examples "
            "ORDER BY created_at DESC LIMIT $1",
            [limit],
        )
        return [
            {"question": row[0], "sql": row[1]}
            for row in result["rows"]
        ]
    except Exception:
        return []
