# ops/backend/config/

Configuration and environment variable management for the Operations Center backend.

## Files

| File | Purpose |
|------|---------|
| `settings.py` | Loads env vars via `python-dotenv` — PostgreSQL URI, MongoDB URI |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_URI` | — | Full PostgreSQL connection string (includes credentials) |
| `MONGODB_URI` | — | Full MongoDB connection string (includes credentials + `?authSource=admin`) |
| `MONGODB_DB_NAME` | `genbi` | MongoDB database name |

Copy `.env.example` to `.env` and fill in credentials before running. In Docker, service hostnames (`postgres`, `mongodb`) replace `localhost`.
