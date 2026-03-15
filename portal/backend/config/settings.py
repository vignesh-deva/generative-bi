import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

# PostgreSQL
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:genbi@localhost:5432/genbi")

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "genbi")
