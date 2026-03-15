# `portal/backend/rag/`

> Retrieval-Augmented Generation — pgvector store and document loader for few-shot SQL example retrieval.

## Overview

This folder implements the RAG layer that retrieves relevant SQL examples for a given user question. The retrieved examples are passed to the SQL Agent as few-shot demonstrations, grounding it in real query patterns rather than generating SQL blind.

The vector store is **pgvector** (PostgreSQL extension), co-hosted in the same PostgreSQL instance as the FMCG data. The **Operations Center** (separate app) provides a UI for the BI/dev team to curate the example corpus — reviewing agent-generated SQL from chat feedback and saving good/corrected queries as new few-shot examples.

## Files

| File | Purpose |
|------|---------|
| `vector_store.py` | pgvector store management — upsert, delete, and similarity-search few-shot examples |
| `documents.py` | Document definitions — the NL question + SQL pairs used as few-shot examples |
| `__init__.py` | Package init |

## How It Fits the Pipeline

```mermaid
flowchart LR
    Q[User Question] -->|embed + search| VS[pgvector Store]
    VS -->|top-k similar examples| RAG[RAG Agent]
    RAG -->|few-shot examples| SQL[SQL Agent]
```

The RAG Agent embeds the incoming question, finds the top-k most similar NL→SQL pairs from the vector store, and passes them as examples in the SQL Agent's prompt.

## Planned Functionality

### `documents.py`
Defines the corpus of NL question + PostgreSQL query pairs. These cover common FMCG supply chain analytics patterns:
- Sales trends by product, brand, region, period
- Inventory levels and low-stock alerts
- Order fulfilment rates by distributor
- Top/bottom performers

### `vector_store.py`
```python
async def upsert_example(doc: Document) -> None
async def delete_example(doc_id: str) -> None
async def search(query: str, top_k: int = 3) -> list[Document]
```

## Design Choices

- **pgvector over a separate vector DB**: Runs in the same PostgreSQL instance as the FMCG data — no extra service to manage. Fast enough for a small corpus of a few hundred examples; scales further if needed.
- **RAG as few-shot, not answer path**: Retrieved examples go into the SQL Agent's prompt as demonstrations. The LLM still generates the final SQL — RAG just anchors it to known-good patterns.
- **Curated via Operations Center**: The BI/dev team reviews chat feedback (thumbs up/down), inspects agent-generated SQL, and saves good or corrected queries to the pgvector table. This creates a human-in-the-loop feedback loop that continuously improves NL → SQL accuracy.
- **Static corpus as bootstrap**: The initial example corpus is hand-curated for FMCG supply chain queries. Over time, curated examples from real chat sessions grow the corpus organically.

## TODO

- [ ] Both files are currently empty scaffolds — implementation pending
- [ ] Decide on embedding model — needs to work with the configured LLM endpoint (sentence-transformers, nomic-embed, or Ollama embeddings)
- [ ] Define the initial example corpus in `documents.py` — aim for 20–50 diverse NL/SQL pairs covering the key analytics use cases
- [ ] pgvector table name should come from `settings.py` (`PGVECTOR_TABLE`)
- [ ] Ops-backend needs read/write access to the pgvector table for RAG curation (via shared PostgreSQL connection)

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Migrated from FAISS to pgvector; updated design choices and API signatures |
| 2026-03-11 | Initial README — scaffolded, implementation pending |
