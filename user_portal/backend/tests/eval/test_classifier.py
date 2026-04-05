"""
Eval: Classifier agent — intent detection accuracy.

Calls the real LLM.  Each case asserts the expected intent is returned.
Expected pass rate: ≥ 90% (9/10 cases).

Run:  RUN_EVAL=1 python -m pytest tests/eval/test_classifier.py -v
"""

import os
import pytest
from agents.classifier import classify

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_EVAL"), reason="Set RUN_EVAL=1 to run eval tests"
)

# ── Test cases ─────────────────────────────────────────────────────
# (query, expected_intent)

ANALYTICS_CASES = [
    ("What is the total revenue by zone for Q1 2025?", "analytics"),
    ("Show me the top 10 distributors by order volume", "analytics"),
    ("Which products are currently out of stock?", "analytics"),
    ("What is the gross profit margin for Beverages this year?", "analytics"),
    ("How many orders were cancelled in the West zone last quarter?", "analytics"),
    ("What is the average delivery time per zone?", "analytics"),
    ("Compare month-over-month sales growth for Snacks vs Dairy", "analytics"),
]

CHITCHAT_CASES = [
    ("Hello there, how are you doing today?", "chitchat"),
    ("Thanks for the help, that was great!", "chitchat"),
    ("What is the capital of France?", "chitchat"),
]

HISTORY_CASES = [
    ("What did I ask you about earlier in this session?", "history"),
]

# "show me performance" is genuinely ambiguous — no time range, no metric
AMBIGUOUS_CASES = [
    ("Just give me some performance data, whatever you have", "ambiguous"),
]

ALL_CASES = ANALYTICS_CASES + CHITCHAT_CASES + HISTORY_CASES + AMBIGUOUS_CASES


# ── Parametrized tests ─────────────────────────────────────────────


@pytest.mark.parametrize("query,expected", ALL_CASES, ids=[c[0][:50] for c in ALL_CASES])
async def test_classifier_intent(query, expected):
    intent = await classify(query)
    assert intent == expected, (
        f"Query: {query!r}\n"
        f"Expected: {expected!r}  Got: {intent!r}"
    )


# ── Follow-up resolution ────────────────────────────────────────────
# Verify the classifier uses chat history to resolve follow-up queries.


async def test_follow_up_classified_as_analytics():
    """'Break that down by month' should resolve to analytics given revenue history."""
    history = [
        {"role": "user", "content": "What is total revenue by zone?"},
        {"role": "assistant", "content": "North zone leads with $1.25M..."},
    ]
    intent = await classify("Break that down by month", chat_history=history)
    assert intent == "analytics", (
        "Follow-up with analytics history should be classified as 'analytics', "
        f"got {intent!r}"
    )


async def test_ambiguous_without_context_resolved_with_context():
    """'Show me that by category' is ambiguous alone but analytics with history."""
    history = [
        {"role": "user", "content": "What is total revenue by zone?"},
        {"role": "assistant", "content": "North zone leads with $1.25M..."},
    ]
    intent = await classify("Show me that breakdown by category instead", chat_history=history)
    assert intent == "analytics"
