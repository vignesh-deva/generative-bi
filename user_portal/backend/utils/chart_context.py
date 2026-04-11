"""Shared helper for rendering a user-attached chart context into a prompt.

Used by the Rewriter, Schema Linker, SQL Agent, and Insight Agent. Keeping
the block identical across agents means the LLM sees a consistent "Reference
Chart" section regardless of which stage it's reasoning about.
"""

from __future__ import annotations


def format_chart_context_block(chart_context: dict | None) -> str:
    """Render the attached-chart block, or an empty string if none is attached.

    Returned string already includes leading newlines so it can be appended
    to a system prompt unconditionally.
    """
    if not chart_context:
        return ""

    title = chart_context.get("title", "")
    sql_query = chart_context.get("sql_query", "")
    if not title and not sql_query:
        return ""

    return (
        "\n\n## Reference Chart (attached by user)\n"
        f"Title: {title}\n"
        "SQL:\n"
        f"{sql_query}\n\n"
        "The user's question is about this chart. Treat the chart's SQL as "
        "ground truth for the filters, joins, and grain the user is currently "
        "looking at. When the question is ambiguous, assume it is a follow-up "
        "on this chart."
    )
