# ops/backend/api/

FastAPI route modules for the Operations Center.

## Endpoints

| Module | Routes | Purpose |
|--------|--------|---------|
| `tickets.py` | `/tickets` | CRUD for dashboard development requests submitted by business users |
| `feedback.py` | `/feedback` | List and review chat feedback (thumbs-up/down), view associated SQL queries |
| `rag_admin.py` | `/rag` | Add, update, delete few-shot NL→SQL examples in pgvector |

## Data Sources

- **MongoDB** — reads chat sessions, messages, and feedback
- **PostgreSQL** — reads FMCG data for SQL validation/testing, writes curated examples to pgvector
