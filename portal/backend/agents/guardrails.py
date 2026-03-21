"""
Guardrails agent — checks for prompt injection and unsafe requests.

Returns (passed: bool, reason: str).
"""

import re

# Patterns that suggest SQL injection or prompt manipulation
UNSAFE_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\b",
    r"UNION\s+SELECT",
    r"--\s*$",
    r"\/\*.*\*\/",
    r"xp_cmdshell",
    r"EXEC\s*\(",
    r"EXECUTE\s*\(",
    r"INTO\s+OUTFILE",
    r"LOAD_FILE",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in UNSAFE_PATTERNS]


async def check_guardrails(query: str) -> tuple[bool, str]:
    for pattern in COMPILED_PATTERNS:
        if pattern.search(query):
            return False, f"Query blocked: potentially unsafe pattern detected"

    if len(query) > 2000:
        return False, "Query blocked: input too long"

    return True, "passed"
