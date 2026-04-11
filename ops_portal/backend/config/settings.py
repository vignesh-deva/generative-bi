import os
from dotenv import load_dotenv

load_dotenv()

# Auth
PORTAL_USERNAME = os.getenv("PORTAL_USERNAME", "testuser")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "testpass")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")

# PostgreSQL
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:genbi@localhost:5432/genbi")

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "genbi")

# Embeddings — used by the feedback→RAG promotion flow to compute vectors and
# check similarity against existing fewshot_examples rows.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "30"))

# Feedback curation policy: anything whose NL question matches an existing
# fewshot at >= this cosine similarity is considered a duplicate and hidden
# from the ops review list by default.
RAG_DEDUP_THRESHOLD = float(os.getenv("RAG_DEDUP_THRESHOLD", "0.80"))
