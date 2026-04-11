# graph/

LangGraph workflow definition for the agent pipeline.

## Files

| File | Purpose |
|------|---------|
| `pipeline.py` | Graph definition — nodes, edges, fan-out/fan-in, state schema |

## Pipeline Flow

```
User Query
         │
  Fetch Chat History (MongoDB)
         │
   Query Rewriter (skips if no history)
         │
    ├── Guardrails (safety)    ─┐
    ├── Classifier (intent)     ├── parallel fan-out
    ├── RAG Agent (few-shot)    │
    └── Schema Agent (schema) ─┘
         │
    Router (fan-in)
    ├── non-analytics → Response Agent → SSE → END
    └── analytics ↓
         │
   Semantic Layer
         │
      SQL Agent ◄─────────────────────────────────────┐
         │                                             │
   Dry-Run Validator                                   │
    ├── fails  → Error Classifier → Correction Agent ──┘ (max 3 retries)
    └── passes ↓
         │
  Execute Query (PostgreSQL)
         │
  Validation Agent (agentic tool loop)
    ├── incorrect → Error Classifier → Correction Agent ─┘
    └── correct ↓
         │
   Insight Agent
         │
  SSE stream → Frontend
```

## State

The LangGraph state object accumulates context as it flows through nodes:

- `query` — original user question
- `rewritten_query` — follow-up-resolved query from Query Rewriter
- `chat_history` — recent messages fetched from MongoDB
- `intent` — classified intent from Classifier
- `guardrail_result` — pass/fail from Guardrails
- `few_shot_examples` — retrieved NL→SQL pairs from RAG
- `schema_context` — relevant table/column metadata + value samples
- `sql_query` — generated SQL
- `validation_result` — pass/fail + error feedback
- `retry_count` — self-repair iteration counter (max 3)
- `query_result` — executed query rows
- `insight` — generated explanation
