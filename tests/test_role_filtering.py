"""Role scoping is applied inside the vector search, not after it."""

import shutil
from unittest.mock import patch

import pytest
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.rag_utils import rag_module


class DeterministicEmbeddings(Embeddings):
    """Stand-in for a real embedder so these tests need no API key."""

    def embed_documents(self, texts):
        return [[float(len(t) % 7), 1.0] for t in texts]

    def embed_query(self, text):
        return [float(len(text) % 7), 1.0]


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "chroma"
    shutil.rmtree(path, ignore_errors=True)
    vs = Chroma(
        collection_name="role_filter_test",
        persist_directory=str(path),
        embedding_function=DeterministicEmbeddings(),
    )
    vs.add_documents(
        [
            Document(page_content=f"record {i} confidential", metadata={"role": role})
            for i, role in enumerate(
                ["finance", "hr", "general", "finance", "hr", "finance", "compliance"]
            )
        ]
    )
    return vs


def retrieve_as(store, role, k=3):
    with patch.object(rag_module, "get_vectorstore", return_value=store):
        with patch.object(rag_module.config, "RETRIEVAL_K", k):
            return rag_module.get_retriever(role, cohere_api_key=None).invoke(
                "confidential"
            )


def test_hr_never_sees_other_departments(store):
    roles = {d.metadata["role"] for d in retrieve_as(store, "HR")}
    assert roles <= {"hr", "general"}


def test_finance_never_sees_hr(store):
    roles = {d.metadata["role"] for d in retrieve_as(store, "Finance")}
    assert "hr" not in roles and "compliance" not in roles


def test_filter_is_a_prefilter_not_a_postfilter(store):
    """A post-filter would fetch the global top-k then discard.

    With 3 finance, 2 hr, 1 general and 1 compliance document, an HR user
    asking for k=3 gets a full 3 only if the constraint was applied during the
    search. Post-filtering the global top-3 would return fewer.
    """
    assert len(retrieve_as(store, "HR", k=3)) == 3


def test_admin_is_unrestricted(store):
    roles = {d.metadata["role"] for d in retrieve_as(store, "Admin", k=7)}
    assert len(roles) > 2


def test_general_role_sees_only_general(store):
    roles = {d.metadata["role"] for d in retrieve_as(store, "General")}
    assert roles == {"general"}
