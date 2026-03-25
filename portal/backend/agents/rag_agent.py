"""
RAG agent — retrieves few-shot NL-to-SQL examples via pgvector cosine similarity.

Returns a list of {question, sql, similarity} dicts for use as few-shot context
in the SQL Agent's prompt.
"""

from agents.tools.rag_tools import retrieve_fewshots


async def retrieve_examples(query: str, limit: int = 5) -> list[dict]:
    """Retrieve few-shot examples by semantic similarity.

    Returns list of {question, sql, similarity} ordered by similarity desc.
    The top similarity score is used by the Decomposer to decide whether
    to skip decomposition (>= 0.85 threshold).
    """
    return await retrieve_fewshots(query, limit=limit)
