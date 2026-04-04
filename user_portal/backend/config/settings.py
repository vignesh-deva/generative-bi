import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_MODEL_SMALL = os.getenv("LLM_MODEL_SMALL", LLM_MODEL)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MAX_SQL_RETRIES = int(os.getenv("MAX_SQL_RETRIES", "3"))
DOMAIN_DESCRIPTION = os.getenv("DOMAIN_DESCRIPTION", "FMCG supply chain analytics")

# PostgreSQL
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:genbi@localhost:5432/genbi")

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "genbi")
