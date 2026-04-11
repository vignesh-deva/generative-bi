"""
Embedding utility for the ops backend.

Mirrors user_portal/backend/agents/tools/rag_tools.py:get_embedding so the
two services can stay self-contained (per architecture: each portal has its
own FastAPI app and deps). Used by the feedback → RAG promotion flow to
compute vectors for candidate questions and for the similarity dedup check.
"""

from openai import AsyncOpenAI

from config.settings import (
    LLM_BASE_URL,
    LLM_API_KEY,
    EMBEDDING_MODEL,
    LLM_REQUEST_TIMEOUT,
)

_client = AsyncOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    timeout=LLM_REQUEST_TIMEOUT,
)


async def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    response = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding
