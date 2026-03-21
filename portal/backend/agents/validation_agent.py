"""
Validation agent — checks generated SQL for correctness and safety.

Returns (passed: bool, feedback: str).
Feedback is passed back to SQL Agent on retry.
"""

import re

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

FORBIDDEN_PATTERNS = [
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bLOAD_FILE\b",
]

COMPILED_FORBIDDEN = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]

SYSTEM_PROMPT = """You are a SQL validation expert. Review the following PostgreSQL SELECT query for:

1. Syntax errors
2. Missing or incorrect table/column references based on the schema
3. Logical issues (wrong JOINs, missing GROUP BY, etc.)

Schema:
{schema}

If the query is valid, respond with exactly: VALID
If there are issues, respond with: INVALID: <brief description of what's wrong>"""


async def validate_sql(sql: str, schema_context: str) -> tuple[bool, str]:
    for pattern in COMPILED_FORBIDDEN:
        if pattern.search(sql):
            return False, "SQL contains forbidden statements (only SELECT allowed)"

    normalized = sql.strip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False, "SQL must start with SELECT or WITH"

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(schema=schema_context),
            },
            {"role": "user", "content": sql},
        ],
        temperature=0,
        max_tokens=200,
    )

    result = response.choices[0].message.content.strip()
    if result.upper().startswith("VALID"):
        return True, ""
    return False, result.replace("INVALID:", "").strip()
