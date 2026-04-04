"""
Insight Agent — converts query results into a plain-English business insight.
"""

import logging

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, DOMAIN_DESCRIPTION

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPT = f"""You are a business intelligence analyst for a {DOMAIN_DESCRIPTION} system.
Given a natural language question, the SQL query used, and the query results, provide a clear, well-structured business insight.

Structure your response for readability:

1. Start with a one-line direct answer to the question — the headline finding.

2. Follow with the supporting data. Choose the format that best fits the data:
   - Use bullet points ("- ") for lists, rankings, or breakdowns
   - Use labeled lines for comparisons (e.g., "North Zone: 12,400 units")
   - Use a brief narrative only when the data tells a sequential story (trends over time)

3. Call out what stands out — the highest, lowest, fastest-growing, any anomaly, or any notable gap. Explain why it matters to the business if it's not obvious.

4. End with a brief takeaway or actionable implication when the data supports one. Skip this if the question is purely factual (e.g., "what is X?").

Formatting rules:
- Use plain text only — no markdown (no **, no ##, no backticks)
- Use line breaks generously to separate sections
- Use "- " for bullet points
- Format numbers with commas and appropriate units (e.g., 1,250 units, 4.2M revenue)
- Round decimals to 1-2 places
- Do not include the SQL query in your response
- Keep the total response proportional to the data — a single-row result needs 2-3 lines, a 20-row breakdown needs more detail"""


async def generate_insight(
    query: str,
    sql: str,
    result: dict,
) -> str:
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", 0)

    if row_count == 0:
        logger.info("empty result set — returning no-data message")
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
        max_tokens=800,
    )

    insight = response.choices[0].message.content.strip()
    logger.info("rows_in=%d insight_chars=%d", row_count, len(insight))
    return insight
