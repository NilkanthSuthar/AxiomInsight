"""Document indexing and the role-scoped retrieval chain."""

import sqlite3
from pathlib import Path

import pandas as pd
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .. import config, vectorstores

# ==============================
# Vector store (lazily created)
# ==============================
# Built on first use rather than at import time, so the module can be imported
# without an OpenAI key present. Without this, `import app.main` crashes on a
# fresh clone before FastAPI ever starts.
_vectorstore = None
_backend = None


def get_backend() -> vectorstores.VectorStoreBackend:
    """The configured vector-store backend (chroma by default)."""
    global _backend
    if _backend is None:
        _backend = vectorstores.get_backend()
    return _backend


def get_vectorstore() -> VectorStore:
    global _vectorstore
    if _vectorstore is None:
        embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            api_key=config.require_openai_key(),
        )
        _vectorstore = get_backend().create(embeddings)
    return _vectorstore


# ==============================
# Indexing
# ==============================
def embed_documents_to_vectorstore(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    get_vectorstore().add_documents(splits)
    print(f"Embedded {len(splits)} chunks into the vector store.")


def load_file(filepath, role):
    """Read one file into LangChain Documents tagged with the owning role."""
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".csv":
            frame = pd.read_csv(filepath)
            return [
                Document(
                    page_content="\n".join(f"{k}: {v}" for k, v in row.items()),
                    metadata={"role": role.lower(), "source": Path(filepath).name},
                )
                for row in frame.to_dict(orient="records")
            ]

        if ext == ".md":
            with open(filepath, "r", encoding="utf-8") as handle:
                content = handle.read()
            return [
                Document(
                    page_content=content,
                    metadata={"role": role.lower(), "source": Path(filepath).name},
                )
            ]

        return None

    except Exception as exc:
        print(f"Failed to process {filepath}: {exc}")
        return None


def run_indexer():
    """Embed every document row not yet marked as embedded.

    Rows are only marked embedded once the embedding call has succeeded, so a
    failure part-way leaves the work to be retried rather than silently skipped.
    """
    conn = sqlite3.connect(config.SQLITE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filepath, role FROM documents WHERE embedded = 0")

        all_docs, indexed_ids = [], []
        for doc_id, path, role in cursor.fetchall():
            docs = load_file(path, role)
            if docs:
                all_docs.extend(docs)
                indexed_ids.append(doc_id)

        if all_docs:
            embed_documents_to_vectorstore(all_docs)
            cursor.executemany(
                "UPDATE documents SET embedded = 1 WHERE id = ?",
                [(i,) for i in indexed_ids],
            )
            conn.commit()
    finally:
        # Without this, an embedding failure left an open write transaction
        # holding a lock on the SQLite file.
        conn.close()

    print(f"Indexed {len(all_docs)} documents.")


# ==============================
# Prompt and model
# ==============================
system_prompt = (
    "You are an assistant for summarizing and answering queries from internal company documents.\n"
    "Always use the retrieved context to answer the query, even if partial.\n"
    "Do not guess. If data is not found, explain what you searched for.\n"
    "When responding:\n"
    "- Add **Source** from document metadata if possible.\n"
    "- Use headers\n"
    "- Use bullet points\n"
    "- For CSV-style data, format in table with two columns\n"
    "\n{context}"
)

chat_prompt = ChatPromptTemplate.from_messages(
    [("system", system_prompt), ("human", "{input}")]
)


def get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=config.ANSWER_MODEL,
        temperature=0.2,
        streaming=True,
        api_key=config.require_openai_key(),
    )


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# ==============================
# Retrieval
# ==============================
def build_role_filter(user_role: str):
    """Metadata filter for the documents a role may read.

    Delegated to the active backend, which owns its own filter dialect. The
    filter is passed into the store's query call, so restricted documents are
    never scored or returned: it is a pre-filter, not a trimming of results
    after the fact.

    Admin is the only unrestricted role; every other role sees its own
    documents plus anything tagged 'general'.
    """
    return get_backend().role_filter(user_role)


def wrap_with_reranker(retriever, cohere_api_key: str, top_n: int = None):
    """Wrap a retriever so Cohere reorders candidates by relevance."""
    reranker = CohereRerank(
        model="rerank-english-v3.0",
        cohere_api_key=cohere_api_key,
        top_n=top_n or config.RETRIEVAL_K,
    )
    return ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=retriever
    )


def get_retriever(user_role: str, cohere_api_key: str = None):
    """Role-scoped retriever, reranked when a Cohere key is configured."""
    cohere_api_key = cohere_api_key or config.COHERE_API_KEY
    role_filter = build_role_filter(user_role)

    # Pull a wider candidate set when reranking, so the reranker has something
    # to choose between; otherwise fetch exactly what we intend to use.
    k = config.RERANK_CANDIDATES if cohere_api_key else config.RETRIEVAL_K

    search_kwargs = {"k": k}
    if role_filter is not None:
        search_kwargs["filter"] = role_filter

    retriever = get_vectorstore().as_retriever(
        search_kwargs=search_kwargs, search_type="similarity"
    )

    if cohere_api_key:
        retriever = wrap_with_reranker(retriever, cohere_api_key)

    return retriever


def get_rag_chain(user_role: str, cohere_api_key: str = None):
    cohere_api_key = cohere_api_key or config.COHERE_API_KEY
    retriever = get_retriever(user_role, cohere_api_key)

    chain = (
        RunnableParallel(
            context=retriever | format_docs,
            input=RunnablePassthrough(),
        )
        | chat_prompt
        | get_model()
        | StrOutputParser()
    )

    # Tag the run so traces are filterable by the things that actually vary
    # between requests: which role scoped the retrieval, whether reranking was
    # in the path, and which store served it. Without this a trace list is a
    # wall of identical-looking runs.
    chain = chain.with_config(
        run_name="rag_answer",
        tags=[
            f"role:{user_role.lower()}",
            f"store:{get_backend().name}",
            "rerank:on" if cohere_api_key else "rerank:off",
        ],
        metadata={
            "user_role": user_role.lower(),
            "vector_store": get_backend().name,
            "reranked": bool(cohere_api_key),
            "retrieval_k": config.RETRIEVAL_K,
        },
    )

    return chain | (lambda text: {"answer": text})
