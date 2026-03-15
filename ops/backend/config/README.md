# ops/backend/config/

Configuration and environment variable management for the Operations Center backend.

## Files

| File | Purpose |
|------|---------|
| `settings.py` | Loads env vars via `python-dotenv` — PostgreSQL URI, MongoDB URI |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_URI` | `postgresql://genbi:genbi@localhost:5432/genbi` | PostgreSQL connection string |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `genbi` | MongoDB database name |

In Docker, these point to service names (`postgres`, `mongodb`) instead of `localhost`.
