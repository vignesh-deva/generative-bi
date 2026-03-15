"""
Schema introspection helpers for Generative BI Agent.

Used by the Schema Agent to describe the database structure to the LLM,
enabling accurate NL → SQL generation without hallucinating column names.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from backend.db.database import get_readonly_connection


@dataclass
class ColumnInfo:
    name: str
    type: str
    not_null: bool
    primary_key: bool
    default: str | None


@dataclass
class ForeignKey:
    column: str
    references_table: str
    references_column: str


@dataclass
class TableSchema:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Render the table as a concise DDL-style block for LLM prompts."""
        lines = [f"Table: {self.name}"]
        for col in self.columns:
            flags = []
            if col.primary_key:
                flags.append("PK")
            if col.not_null and not col.primary_key:
                flags.append("NOT NULL")
            if col.default is not None:
                flags.append(f"DEFAULT {col.default}")
            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            lines.append(f"  {col.name}  {col.type}{flag_str}")
        for fk in self.foreign_keys:
            lines.append(f"  FK: {fk.column} → {fk.references_table}.{fk.references_column}")
        return "\n".join(lines)


def get_table_names() -> list[str]:
    """Return all user table names in the database (excludes sqlite_* internals)."""
    with get_readonly_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def get_table_schema(table_name: str) -> TableSchema:
    """Introspect a single table and return its schema."""
    with get_readonly_connection() as conn:
        col_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        fk_rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()

    columns = [
        ColumnInfo(
            name=row["name"],
            type=row["type"],
            not_null=bool(row["notnull"]),
            primary_key=bool(row["pk"]),
            default=row["dflt_value"],
        )
        for row in col_rows
    ]

    foreign_keys = [
        ForeignKey(
            column=row["from"],
            references_table=row["table"],
            references_column=row["to"],
        )
        for row in fk_rows
    ]

    return TableSchema(name=table_name, columns=columns, foreign_keys=foreign_keys)


def get_full_schema() -> list[TableSchema]:
    """Return schema info for every table in the database."""
    return [get_table_schema(name) for name in get_table_names()]


def get_schema_prompt() -> str:
    """Return a ready-to-use schema description string for LLM prompts.

    The Schema Agent passes this directly into the SQL Agent's system prompt
    so the LLM knows every table, column, type, and foreign-key relationship.
    """
    tables = get_full_schema()
    sections = [t.to_prompt_text() for t in tables]
    header = (
        "Database: SQLite — FMCG Supply Chain (Indian F&B, Jan–Dec 2025)\n"
        "All dates stored as ISO text (YYYY-MM-DD). Monetary values in INR.\n"
        "─" * 60
    )
    return header + "\n\n" + "\n\n".join(sections)
