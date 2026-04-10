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
