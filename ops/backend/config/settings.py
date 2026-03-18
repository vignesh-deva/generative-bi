import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:genbi@localhost:5432/genbi")

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "genbi")
