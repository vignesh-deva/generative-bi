"""
Classifier agent — determines the intent of the user's query.

Returns one of: "analytics", "chitchat", "out_of_scope"
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPT = """You are an intent classifier for an FMCG supply chain analytics system.
Classify the user's question into exactly one category:

- "analytics" — questions about sales, revenue, orders, products, inventory, shipments, zones, distributors, retailers, or any data query
- "chitchat" — greetings, small talk, jokes, general conversation
- "out_of_scope" — questions unrelated to FMCG supply chain (politics, weather, coding help, etc.)

Respond with ONLY the category name, nothing else."""


async def classify(query: str) -> str:
    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=20,
    )
    intent = response.choices[0].message.content.strip().lower()
    if intent not in ("analytics", "chitchat", "out_of_scope"):
        return "analytics"
    return intent
