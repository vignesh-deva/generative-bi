# `backend/rag/`

> Retrieval-Augmented Generation — FAISS vector store and document loader for few-shot SQL example retrieval.

## Overview

This folder implements the RAG layer that retrieves relevant SQL examples for a given user question. The retrieved examples are passed to the SQL Agent as few-shot demonstrations, grounding it in real query patterns rather than generating SQL blind. The vector store is FAISS, running entirely locally — no cloud vector DB.

## Files

| File | Purpose |
|------|---------|
| `vector_store.py` | FAISS index management — build, persist, load, and query the vector store |
| `documents.py` | Document definitions — the NL question + SQL pairs used as few-shot examples |
| `__init__.py` | Package init |

## How It Fits the Pipeline

```mermaid
flowchart LR
    Q[User Question] -->|embed + search| VS[FAISS Vector Store]
    VS -->|top-k similar examples| RAG[RAG Agent]
    RAG -->|few-shot examples| SQL[SQL Agent]
```

The RAG Agent embeds the incoming question, finds the top-k most similar NL→SQL pairs from the vector store, and passes them as examples in the SQL Agent's prompt.

## Planned Functionality

### `documents.py`
Defines the corpus of NL question + SQLite query pairs. These cover common FMCG supply chain analytics patterns:
- Sales trends by product, brand, region, period
- Inventory levels and low-stock alerts
- Order fulfilment rates by distributor
- Top/bottom performers

### `vector_store.py`
```python
def build_index(documents: list[Document]) -> FAISSIndex
def save_index(index, path: str) -> None
def load_index(path: str) -> FAISSIndex
def search(index, query: str, top_k: int = 3) -> list[Document]
```

## Design Choices

- **FAISS over cloud vector DB**: Keeps everything local — no Pinecone, no Weaviate. FAISS is fast enough for a small corpus of a few hundred examples.
- **RAG as few-shot, not answer path**: Retrieved examples go into the SQL Agent's prompt as demonstrations. The LLM still generates the final SQL — RAG just anchors it to known-good patterns.
- **Static document corpus initially**: The example corpus is hand-curated for FMCG supply chain queries. Dynamic addition (e.g. saving successful queries) can be added later.

## TODO

- [ ] Both files are currently empty scaffolds — implementation pending
- [ ] Decide on embedding model — needs to be local (sentence-transformers, nomic-embed, or Ollama embeddings)
- [ ] Define the initial example corpus in `documents.py` — aim for 20–50 diverse NL/SQL pairs covering the key analytics use cases
- [ ] FAISS index persistence path should come from `settings.py`
- [ ] Consider adding the user's successful past queries to the index over time (self-improving few-shot)

## Changelog

| Date | Change |
|------|--------|
| 2026-03-11 | Initial README — scaffolded, implementation pending |
