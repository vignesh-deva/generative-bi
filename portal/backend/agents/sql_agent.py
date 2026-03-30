"""
SQL Agent — generates PostgreSQL SELECT queries from natural language.

Includes two sub-agents (invoked as internal calls):
  - Decomposer: decides if the query needs multi-step decomposition
  - Sub-query Generator: generates SQL for each sub-query step

Receives: schema context, semantic context, RAG few-shot examples, chat history.
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

RAG_SIMILARITY_THRESHOLD = 0.85

# ── Decomposer sub-agent ────────────────────────────────────────

DECOMPOSER_PROMPT = f"""You are a query decomposer for a {DOMAIN_DESCRIPTION} database.
Given a natural language question, decide if it can be answered with a single SQL query
or needs to be broken into sub-steps.

Rules:
- Most questions can be answered with a single query (JOINs, GROUP BY, subqueries)
- Only decompose if the question involves fundamentally different data that can't be combined in one query
- If decomposing, list the sub-queries as numbered steps

If single query: respond with exactly "SINGLE"
If multi-step: respond with:
MULTI
1. <sub-question 1>
2. <sub-question 2>
..."""


async def _decompose(query: str, few_shot_examples: list[dict]) -> dict:
    """Decide whether to decompose the query or use a matched RAG example directly.

    Returns:
        {"strategy": "single"} — generate one query
        {"strategy": "adapt", "matched": {...}} — adapt a high-similarity RAG match
        {"strategy": "multi", "steps": [...]} — decompose into sub-queries
    """
    # Check if RAG has a high-similarity match
    if few_shot_examples:
        top = few_shot_examples[0]
        if top.get("similarity", 0) >= RAG_SIMILARITY_THRESHOLD:
            return {"strategy": "adapt", "matched": top}

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": DECOMPOSER_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=200,
    )

    result = response.choices[0].message.content.strip()
    if result.upper().startswith("SINGLE"):
        return {"strategy": "single"}

    # Parse multi-step plan
    steps = []
    for line in result.split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            steps.append(line.split(".", 1)[1].strip())
    if not steps:
        return {"strategy": "single"}

    return {"strategy": "multi", "steps": steps}


# ── SQL generation prompt ────────────────────────────────────────

SYSTEM_PROMPT = """You are a PostgreSQL SQL expert for a {domain} database.
Given the database schema, semantic context, and a natural language question, generate a single SELECT query.

Rules:
- Output ONLY the SQL query, no explanation, no markdown fences
- Use only SELECT statements (no INSERT, UPDATE, DELETE, DDL)
- Use proper JOINs based on foreign keys shown in the schema
- Use table aliases for readability
- Format numbers appropriately (ROUND for decimals)
- Limit results to 50 rows unless the user asks for more
- Follow the metric definitions and business rules in the semantic context

Database schema:
{schema}

{semantic}

{fewshots}

{history}"""


def _format_fewshots(examples: list[dict]) -> str:
    if not examples:
        return ""
    lines = ["Few-shot examples (similar queries and their SQL):"]
    for i, ex in enumerate(examples, 1):
        sim = ex.get("similarity", 0)
        lines.append(f"\nExample {i} (similarity: {sim:.2f}):")
        lines.append(f"Q: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
    return "\n".join(lines)


def _format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return ""
    lines = ["Recent conversation context:"]
    for msg in chat_history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:200]
        sql = msg.get("sql_query")
        lines.append(f"  {role}: {content}")
        if sql:
            lines.append(f"  [SQL used: {sql[:200]}]")
    return "\n".join(lines)


async def _generate_single_sql(
    query: str,
    schema_context: str,
    semantic_context: str,
    few_shot_examples: list[dict],
    chat_history: list[dict],
) -> str:
    """Generate a single SQL query."""
    system = SYSTEM_PROMPT.format(
        domain=DOMAIN_DESCRIPTION,
        schema=schema_context,
        semantic=semantic_context,
        fewshots=_format_fewshots(few_shot_examples),
        history=_format_chat_history(chat_history),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=1024,
    )

    sql = response.choices[0].message.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return sql


ADAPT_PROMPT = """You are a PostgreSQL SQL expert. You have a reference query that is very similar to the user's question.
Adapt the reference SQL to answer the user's specific question. Only change what's necessary (filters, columns, grouping).

Reference question: {ref_question}
Reference SQL: {ref_sql}

Database schema:
{schema}

{semantic}

Output ONLY the adapted SQL query, no explanation, no markdown fences."""


async def _adapt_matched_sql(
    query: str,
    matched: dict,
    schema_context: str,
    semantic_context: str,
) -> str:
    """Adapt a high-similarity RAG match to the user's specific question."""
    system = ADAPT_PROMPT.format(
        ref_question=matched["question"],
        ref_sql=matched["sql"],
        schema=schema_context,
        semantic=semantic_context,
    )

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=1024,
    )

    sql = response.choices[0].message.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return sql


# ── Main entry point ─────────────────────────────────────────────

async def generate_sql(
    query: str,
    schema_context: str,
    semantic_context: str = "",
    few_shot_examples: list[dict] | None = None,
    chat_history: list[dict] | None = None,
) -> str:
    """Generate SQL for the user's query.

    Orchestrates: Decomposer -> (adapt | single | multi-step) SQL generation.
    """
    examples = few_shot_examples or []
    history = chat_history or []

    plan = await _decompose(query, examples)

    if plan["strategy"] == "adapt":
        return await _adapt_matched_sql(
            query, plan["matched"], schema_context, semantic_context
        )

    if plan["strategy"] == "multi":
        # For multi-step, generate a CTE-based query that combines sub-queries
        combined_query = (
            f"This requires a multi-step approach. Steps:\n"
            + "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan["steps"]))
            + "\n\nGenerate a single SQL query (using CTEs/subqueries) that combines all steps."
            + f"\n\nOriginal question: {query}"
        )
        return await _generate_single_sql(
            combined_query, schema_context, semantic_context, examples, history
        )

    # Single strategy (default)
    return await _generate_single_sql(
        query, schema_context, semantic_context, examples, history
    )
