"""
Insight Agent — converts query results into a plain-English business insight.
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, DOMAIN_DESCRIPTION

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPT = f"""You are a business intelligence analyst for a {DOMAIN_DESCRIPTION} system.
Given a natural language question, the SQL query used, and the query results, provide a clear, concise business insight.

Rules:
- Lead with the key finding, then supporting details
- Keep it under 3-4 sentences for simple queries, up to a paragraph for complex ones
- If the results are empty, say so clearly and suggest why
- Don't include the SQL in your response
- Be specific — cite actual numbers from the results
- Use standard number formatting (thousands, millions, etc.)"""


async def generate_insight(
    query: str,
    sql: str,
    result: dict,
) -> str:
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", 0)

    if row_count == 0:
        return (
            "The query returned no results. This could mean the data doesn't "
            "exist for the specified criteria, or the filters may be too restrictive."
        )

    display_rows = rows[:20]
    result_text = f"Columns: {', '.join(columns)}\n"
    for row in display_rows:
        result_text += " | ".join(str(v) for v in row) + "\n"
    if row_count > 20:
        result_text += f"... and {row_count - 20} more rows\n"

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"Query results ({row_count} rows):\n{result_text}"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()
