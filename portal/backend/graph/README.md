# graph/

LangGraph workflow definition for the agent pipeline.

## Files

| File | Purpose |
|------|---------|
| `pipeline.py` | Graph definition — nodes, edges, fan-out/fan-in, state schema |

## Pipeline Flow

```
User Query
    ├── Classifier (intent)       ─┐
    ├── Guardrails (safety)        ├── parallel fan-out
    └── RAG Lookup (few-shot)     ─┘
                 │
           Schema Agent
                 │
            SQL Agent ◄── Validation Agent (max 2 retries)
                 │
         Query Execution (PostgreSQL)
                 │
           Insight Agent
                 │
        SSE stream → Frontend
```

## State

The LangGraph state object accumulates context as it flows through nodes:

- `query` — original user question
- `intent` — classified intent from Classifier
- `guardrail_result` — pass/fail from Guardrails
- `few_shot_examples` — retrieved NL→SQL pairs from RAG
- `schema_context` — relevant table/column metadata
- `sql_query` — generated SQL
- `validation_result` — pass/fail + error feedback
- `query_result` — executed query rows
- `insight` — generated explanation
