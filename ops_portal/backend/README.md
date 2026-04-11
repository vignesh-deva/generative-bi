# ops_portal/backend/

FastAPI — Operations Center APIs for ticket management, feedback review, and RAG curation.

## Endpoints

| Module | Routes | Purpose |
|--------|--------|---------|
| `api/auth.py` | `POST /auth/login` | Issues a 7-day JWT; `verify_token` dependency protects all other routes |
| `api/tickets.py` | `/api/tickets` | List and manage dashboard requests — status transitions, comments |
| `api/feedback.py` | `/api/feedback` | List/review chat feedback, view associated SQL |
| `api/rag.py` | `/api/rag/fewshots` | Add and list few-shot NL→SQL examples in pgvector |

`GET /health` is also public (no token required).

## Auth

All `/api/*` routes require a valid JWT in the `Authorization: Bearer <token>` header. Obtain a token via `POST /auth/login` with `{"username": "...", "password": "..."}`. Credentials are read from `PORTAL_USERNAME` and `PORTAL_PASSWORD` in `.env`.

## Shared Resources

- **MongoDB** — reads chat sessions, messages, and feedback (shared with portal backend)
- **PostgreSQL** — reads FMCG data for SQL validation/testing; writes curated few-shot examples to the pgvector table

## Stack

- FastAPI
- PyJWT (auth)
- asyncpg (PostgreSQL driver)
- Motor (async MongoDB driver)
- Runs on port 8001

## Running

### Docker
```bash
docker compose up ops-backend
```

### Manual
```bash
cd ops_portal/backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Fill in POSTGRES_URI, MONGODB_URI, PORTAL_USERNAME, PORTAL_PASSWORD, JWT_SECRET
uvicorn main:app --reload --port 8001
```
