"""
Query Rewriter agent — resolves follow-up queries into standalone questions.

Takes the raw user message + chat history and produces a self-contained
query that can be understood without conversation context.
Skips the LLM call entirely when there is no chat history.
"""

import logging

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION, LLM_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=LLM_REQUEST_TIMEOUT)

SYSTEM_PROMPT = f"""You are a query rewriter for a {DOMAIN_DESCRIPTION} system.
You will receive a chat history and the user's latest message.

Your job: rewrite the user's message into a standalone, self-contained query that
can be understood WITHOUT the chat history. Resolve all pronouns, references,
and follow-up phrases using the conversation context.

Rules:
- If the message is already self-contained, return it exactly as-is
- Preserve the user's intent — do not add or remove requirements
- Include specific entities, metrics, time periods, and filters from the history
  when the user's message references them implicitly
- Output ONLY the rewritten query, nothing else"""


def _format_history(chat_history: list[dict]) -> str:
    lines = []
    for msg in chat_history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:200]
        lines.append(f"  {role}: {content}")
    return "\n".join(lines)


async def rewrite_query(query: str, chat_history: list[dict] | None = None) -> str:
    """Resolve follow-up references in the query using chat history.

    Returns the query unchanged if there is no history to resolve against.
    """
    if not chat_history:
        logger.info("rewrite=skipped reason=no_history")
        return query

    history_block = _format_history(chat_history)
    user_content = f"Chat history:\n{history_block}\n\nLatest message: {query}"

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
        max_tokens=300,
    )

    rewritten = response.choices[0].message.content.strip()
    if not rewritten:
        logger.warning("rewrite=empty, falling back to original")
        return query

    if rewritten == query:
        logger.info("rewrite=unchanged query=%.120s", query)
    else:
        logger.info("rewrite original=%.120s rewritten=%.120s", query, rewritten)

    return rewritten
