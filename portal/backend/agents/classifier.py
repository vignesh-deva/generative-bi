"""
Classifier agent — determines the intent of the user's query.

Pure LLM call (no tools). Receives recent chat history for follow-up resolution.
Returns one of: "analytics", "chitchat", "history", or "ambiguous"
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION
from config.semantic_layer import SEMANTIC_LAYER

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# Derive analytics-relevant terms from semantic layer at startup (no hardcoding)
_metric_names = [m["name"].split("(")[0].strip() for m in SEMANTIC_LAYER.get("metrics", [])]
_join_tables = list({t for j in SEMANTIC_LAYER.get("join_paths", []) for t in j.get("tables", [])})
_analytics_terms = ", ".join(sorted(set(_metric_names + _join_tables)))

SYSTEM_PROMPT = f"""You are an intent classifier for a {DOMAIN_DESCRIPTION} system.
You will receive the user's message and optionally recent chat history for context.

Classify the user's message into exactly one intent:

- "analytics" — data questions related to the business domain: {_analytics_terms}, or any metric / data query. Also classify follow-up questions about previous analytics results as "analytics".
- "chitchat" — greetings, small talk, jokes, thanks, general conversation, or questions unrelated to the business data (politics, weather, coding, etc.)
- "history" — user asking about their past conversations, wanting a summary of previous chats, or asking "what did I ask before?"
- "ambiguous" — the query is related to analytics but too vague to generate a SQL query (e.g., "tell me about sales" without specifying what metric, time period, or dimension). Only use this when the query genuinely cannot be answered without clarification.

IMPORTANT: Resolve follow-ups using chat history. If the user says "break that down by zone" and the last query was about revenue, classify as "analytics" (not "ambiguous").
IMPORTANT: Lean toward "analytics" when in doubt — most users are here for data questions.

Respond with ONLY the intent name, nothing else."""


def _format_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return ""
    lines = ["Recent chat history:"]
    for msg in chat_history[-6:]:  # last 6 messages (3 turns)
        role = msg.get("role", "user")
        content = msg.get("content", "")[:200]
        lines.append(f"  {role}: {content}")
    return "\n".join(lines)


async def classify(query: str, chat_history: list[dict] | None = None) -> str:
    user_content = query
    if chat_history:
        user_content = f"{_format_history(chat_history)}\n\nCurrent message: {query}"

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
        max_tokens=20,
    )
    intent = response.choices[0].message.content.strip().lower().strip('"')
    if intent not in ("analytics", "chitchat", "history", "ambiguous"):
        return "analytics"
    return intent
