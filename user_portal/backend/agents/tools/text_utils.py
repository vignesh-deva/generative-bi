"""
Small text utilities shared across agents.

  strip_markdown_fences(text)  — remove a leading/trailing ``` or ```lang fence
                                 from an LLM response, whether or not the
                                 fence is followed by a newline.
"""

import re

# Matches an opening fence at the start of the text (``` or ```sql etc.),
# optionally followed by a newline or spaces; and a closing fence at the end.
_OPEN_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*\n?", re.MULTILINE)
_CLOSE_FENCE_RE = re.compile(r"\n?\s*```\s*$", re.MULTILINE)


def strip_markdown_fences(text: str) -> str:
    """Return text with a leading/trailing markdown code fence removed.

    Handles:
      - ```\\nSELECT 1\\n```
      - ```sql\\nSELECT 1\\n```
      - ```sql SELECT 1```   (no newlines)
      - plain text (no fences) — returned unchanged
    """
    if not text:
        return text
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    stripped = _OPEN_FENCE_RE.sub("", stripped, count=1)
    stripped = _CLOSE_FENCE_RE.sub("", stripped, count=1)
    return stripped.strip()
