"""Swappable vector-store backends.

The retrieval path talks to a backend through this interface rather than to
Chroma directly, so the store can be changed with one environment variable:

    VECTOR_STORE=chroma     (default)
    VECTOR_STORE=pinecone

The interface exists because the two stores differ in more than construction.
Each backend owns its own metadata-filter dialect, so the role pre-filter is
expressed correctly for whichever store is in use, and the calling code does
not have to know which that is.

Chroma is the default and the backend this project is developed against.
Pinecone is supported for the case where the index needs to live outside the
process.
"""

from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from . import config


class VectorStoreBackend(ABC):
    """One vector store, plus the filter dialect it expects."""

    name: str

    @abstractmethod
    def create(self, embeddings: Embeddings) -> VectorStore:
        """Return a ready-to-use LangChain vector store."""

    @abstractmethod
    def role_filter(self, role: str) -> dict | None:
        """Metadata filter restricting results to what `role` may read.

        Returns None for unrestricted access. The filter is handed to the
        store's own query call, so it constrains the search itself rather than
        trimming results afterwards.
        """

    def describe(self) -> str:
        return self.name


class ChromaBackend(VectorStoreBackend):
    """Embedded Chroma, persisted to a local directory.

    The default. Needs no server and no network, which is what makes the
    project runnable from a clone without external accounts.
    """

    name = "chroma"

    def create(self, embeddings: Embeddings) -> VectorStore:
        from langchain_chroma import Chroma

        config.ensure_directories()
        return Chroma(
            collection_name=config.CHROMA_COLLECTION,
            persist_directory=str(config.CHROMA_PATH),
            embedding_function=embeddings,
        )

    def role_filter(self, role: str) -> dict | None:
        role = role.lower()
        if role == "admin":
            return None
        if role == "general":
            # Chroma takes a bare equality map for a single condition.
            return {"role": "general"}
        return {"role": {"$in": [role, "general"]}}

    def describe(self) -> str:
        return f"chroma (collection={config.CHROMA_COLLECTION}, path={config.CHROMA_PATH})"


class PineconeBackend(VectorStoreBackend):
    """Managed Pinecone serverless index.

    Requires PINECONE_API_KEY and an index whose dimension matches the
    embedding model (1536 for text-embedding-3-small). The index is created on
    first use if it does not exist.
    """

    name = "pinecone"

    def create(self, embeddings: Embeddings) -> VectorStore:
        # Check configuration before importing: a user who has set neither the
        # key nor installed the optional libraries should be told about the
        # key, not shown an ImportError for a package they never asked for.
        if not config.PINECONE_API_KEY:
            raise config.MissingCredentialError(
                "VECTOR_STORE=pinecone but PINECONE_API_KEY is not set.\n"
                "Set it in .env, or switch back with VECTOR_STORE=chroma."
            )

        try:
            from langchain_pinecone import PineconeVectorStore
            from pinecone import Pinecone, ServerlessSpec
        except ImportError as exc:
            raise ImportError(
                "The Pinecone backend needs its optional client libraries:\n"
                "    pip install -r requirements-pinecone.txt\n"
                "Or switch back with VECTOR_STORE=chroma."
            ) from exc

        client = Pinecone(api_key=config.PINECONE_API_KEY)
        existing = {i["name"] for i in client.list_indexes()}
        if config.PINECONE_INDEX not in existing:
            client.create_index(
                name=config.PINECONE_INDEX,
                dimension=config.EMBEDDING_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=config.PINECONE_CLOUD, region=config.PINECONE_REGION
                ),
            )

        return PineconeVectorStore(
            index=client.Index(config.PINECONE_INDEX),
            embedding=embeddings,
        )

    def role_filter(self, role: str) -> dict | None:
        role = role.lower()
        if role == "admin":
            return None
        # Pinecone expects an explicit operator even for a single value.
        if role == "general":
            return {"role": {"$eq": "general"}}
        return {"role": {"$in": [role, "general"]}}

    def describe(self) -> str:
        return f"pinecone (index={config.PINECONE_INDEX}, region={config.PINECONE_REGION})"


BACKENDS: dict[str, type[VectorStoreBackend]] = {
    "chroma": ChromaBackend,
    "pinecone": PineconeBackend,
}


def get_backend(name: str = None) -> VectorStoreBackend:
    name = (name or config.VECTOR_STORE).lower()
    if name not in BACKENDS:
        raise ValueError(
            f"Unknown VECTOR_STORE {name!r}. Available: {', '.join(sorted(BACKENDS))}"
        )
    return BACKENDS[name]()
