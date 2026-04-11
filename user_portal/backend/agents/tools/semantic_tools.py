"""
Semantic tools — provide semantic layer context to agents.

Tools:
  get_semantic_context(tables)  — metric definitions, join paths, business rules
                                  for the given tables
"""

from config.semantic_layer import SEMANTIC_LAYER


def get_semantic_context(tables: list[str]) -> str:
    """Return semantic layer context filtered to the given tables.

    Includes: metric definitions, FK join paths, business rules,
    and value samples relevant to the specified tables.
    """
    sections = []

    # Metric definitions
    metrics = [
        m for m in SEMANTIC_LAYER.get("metrics", [])
        if not m.get("tables") or any(t in tables for t in m["tables"])
    ]
    if metrics:
        lines = ["METRIC DEFINITIONS:"]
        for m in metrics:
            lines.append(f"  {m['name']}: {m['formula']}")
            if m.get("note"):
                lines.append(f"    Note: {m['note']}")
        sections.append("\n".join(lines))

    # Join paths
    joins = [
        j for j in SEMANTIC_LAYER.get("join_paths", [])
        if any(t in tables for t in j.get("tables", []))
    ]
    if joins:
        lines = ["JOIN PATHS:"]
        for j in joins:
            lines.append(f"  {j['description']}: {j['path']}")
        sections.append("\n".join(lines))

    # Business rules
    rules = [
        r for r in SEMANTIC_LAYER.get("business_rules", [])
        if not r.get("tables") or any(t in tables for t in r["tables"])
    ]
    if rules:
        lines = ["BUSINESS RULES:"]
        for r in rules:
            lines.append(f"  - {r['rule']}")
        sections.append("\n".join(lines))

    # Known values
    values = {
        k: v for k, v in SEMANTIC_LAYER.get("known_values", {}).items()
        if k.split(".")[0] in tables
    }
    if values:
        lines = ["KNOWN VALUES:"]
        for col, vals in values.items():
            lines.append(f"  {col}: {', '.join(str(v) for v in vals)}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) if sections else ""
