"""
SQL Agent — generates a PostgreSQL SELECT query from the user's
natural language question, using schema context and few-shot examples.
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPT = """You are a PostgreSQL SQL expert for an FMCG supply chain database.
Given the database schema and a natural language question, generate a single SELECT query that answers the question.

Rules:
- Output ONLY the SQL query, no explanation, no markdown fences
- Use only SELECT statements (no INSERT, UPDATE, DELETE, DDL)
- Use proper JOINs based on foreign keys
- Use table aliases for readability
- Format numbers appropriately (ROUND for decimals)
- Limit results to 50 rows unless the user asks for more
- Use Indian number formatting context (crores, lakhs) when relevant in aliases

Database schema:
{schema}

{fewshots}"""


def _format_fewshots(examples: list[dict]) -> str:
    if not examples:
        return ""
    lines = ["Few-shot examples:"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"Q: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
    return "\n".join(lines)


async def generate_sql(
    query: str,
    schema_context: str,
    few_shot_examples: list[dict],
    previous_error: str = "",
) -> str:
    system = SYSTEM_PROMPT.format(
        schema=schema_context,
        fewshots=_format_fewshots(few_shot_examples),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]

    if previous_error:
        messages.append(
            {
                "role": "user",
                "content": f"The previous SQL had an error: {previous_error}\nPlease fix and regenerate.",
            }
        )

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=1024,
    )

    sql = response.choices[0].message.content.strip()
    # Strip markdown fences if the model wraps in ```sql ... ```
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return sql
