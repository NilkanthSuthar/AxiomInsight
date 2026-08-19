"""Central configuration.

All settings come from environment variables (optionally via a .env file).
This module replaces the old `rag_utils/secret_key.py`, which held hardcoded
constants, was gitignored, and was therefore missing from every clone.

Paths are anchored to the repository root so the app behaves the same
regardless of the working directory it is started from.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# --- Credentials -----------------------------------------------------------
# None when unset. Callers are expected to degrade gracefully rather than
# crash at import time; see require_openai_key().
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
COHERE_API_KEY = os.getenv("COHERE_API_KEY") or None
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") or None
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY") or None

# --- Storage locations -----------------------------------------------------
SQLITE_PATH = BASE_DIR / os.getenv("DB_PATH", "roles_docs.db")
CHROMA_PATH = BASE_DIR / os.getenv("CHROMA_PATH", "chroma_db")
DUCKDB_PATH = BASE_DIR / os.getenv("DUCKDB_PATH", "static/data/structured_queries.duckdb")
UPLOAD_DIR = BASE_DIR / "static/uploads"

# --- Vector store ----------------------------------------------------------
# "chroma" (default, embedded) or "pinecone" (managed). See app/vectorstores.py.
VECTOR_STORE = os.getenv("VECTOR_STORE", "chroma").lower()
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "my_collection")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "axiom-insight")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# --- Models ----------------------------------------------------------------
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
# Must match the vector index dimension. text-embedding-3-small is 1536.
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

# --- Retrieval -------------------------------------------------------------
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "3"))
# Candidates pulled before reranking. Reranking only helps if it has more
# than RETRIEVAL_K documents to choose from.
RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "10"))

# --- Optional LangSmith tracing --------------------------------------------
# Off unless a key is present AND tracing is explicitly requested. The previous
# code forced tracing on and overwrote whatever was in the environment.
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "axiom-insight")
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def tracing_status() -> str:
    """Human-readable LangSmith tracing state, for /health."""
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        return "enabled"
    if LANGCHAIN_TRACING_V2:
        return "requested but LANGCHAIN_API_KEY is missing"
    return "disabled"


class MissingCredentialError(RuntimeError):
    """Raised when an operation needs an API key that was never configured."""


def require_openai_key() -> str:
    """Return the OpenAI key, or raise with an actionable message."""
    if not OPENAI_API_KEY:
        raise MissingCredentialError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key:\n"
            "    cp .env.example .env\n"
            "Get a key at https://platform.openai.com/api-keys"
        )
    return OPENAI_API_KEY


def ensure_directories() -> None:
    """Create the directories the databases live in."""
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
