# ops_portal/backend/

FastAPI — Operations Center APIs for ticket management, feedback review, and RAG curation.

## Endpoints

| Module | Routes | Purpose |
|--------|--------|---------|
| `api/tickets.py` | `/tickets` | CRUD for dashboard development requests |
| `api/feedback.py` | `/feedback` | List/review chat feedback, view associated SQL |
| `api/rag_admin.py` | `/rag` | Add, update, delete few-shot NL→SQL examples in pgvector |

## Shared Resources

- **MongoDB** — reads chat sessions, messages, and feedback (shared with portal backend)
- **PostgreSQL** — reads FMCG data for SQL validation/testing; writes curated few-shot examples to the pgvector table

## Stack

- FastAPI
- asyncpg (PostgreSQL driver)
- Motor (async MongoDB driver)
- Runs on port 8001
