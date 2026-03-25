"""
Response Agent — handles all non-analytics intents.

Generates appropriate responses for:
  - blocked: polite refusal explaining why the query was blocked
  - ambiguous: asks a clarifying question to narrow down the analytics query
  - chitchat: conversational reply
  - history: fetches chat history from MongoDB, summarizes or answers
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPTS = {
    "blocked": """You are a helpful assistant for an FMCG supply chain analytics system.
The user's query was flagged by our safety system. Politely explain that you cannot process this request.
Be brief, professional, and suggest they rephrase if it was a misunderstanding.
Do not reveal details about the safety system's rules.""",

    "ambiguous": """You are a helpful assistant for an FMCG supply chain analytics system.
The user asked a data-related question that is too vague to answer directly.
Ask a clear, specific clarifying question to help narrow down what they need.

Available data dimensions: products (by brand, category, SKU), geography (zones, states, cities),
channels (Modern Trade, General Trade, E-Commerce), time periods, distributors, wholesalers, retailers.
Available metrics: revenue, units sold, gross profit, margins, order fulfillment, delivery times, inventory levels.

Ask ONE focused question to disambiguate. Keep it conversational and brief.""",

    "chitchat": """You are a friendly assistant for an FMCG supply chain analytics system.
Respond to the user's message conversationally. Keep it brief and natural.
If relevant, gently remind them you're best at answering supply chain and sales data questions.""",

    "history": """You are a helpful assistant for an FMCG supply chain analytics system.
The user is asking about their past conversations. You have their recent chat history below.
Summarize or answer their question based on the history provided.
If there's no relevant history, let them know politely.""",
}


def _format_history_context(chat_history: list[dict]) -> str:
    if not chat_history:
        return "No previous chat history available."
    lines = ["Previous conversations:"]
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:300]
        lines.append(f"  {role}: {content}")
    return "\n".join(lines)


async def generate_response(
    query: str,
    intent: str,
    chat_history: list[dict] | None = None,
    guardrail_reason: str = "",
) -> str:
    """Generate a response for a non-analytics intent."""
    system_prompt = SYSTEM_PROMPTS.get(intent, SYSTEM_PROMPTS["chitchat"])

    user_content = query
    if intent == "blocked" and guardrail_reason:
        user_content = f"[Blocked reason: {guardrail_reason}]\n\nUser message: {query}"
    elif intent == "history" and chat_history:
        user_content = f"{_format_history_context(chat_history)}\n\nUser question: {query}"

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.5,
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()
