"""End-to-end check of the evaluation runner.

Uses a deterministic bag-of-words embedder instead of OpenAI, so the whole
retrieve-and-score path runs with no API key. This tests the mechanism, not
retrieval quality: the real numbers come from scripts/evaluate_retrieval.py
against real embeddings.
"""

import hashlib
import json
import pathlib
import re
from unittest.mock import patch

import pytest
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag_utils import rag_module
from eval.metrics import evaluate

ROOT = pathlib.Path(__file__).parent.parent
UPLOADS = ROOT / "static" / "uploads"
DIMS = 512


class LexicalEmbeddings(Embeddings):
    """Hashed bag-of-words. Deterministic, offline, and actually lexical,
    so overlapping wording genuinely scores higher."""

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * DIMS
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMS
            vec[h] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture(scope="module")
def indexed_store(tmp_path_factory):
    """Index the real sample documents with the offline embedder."""
    store = Chroma(
        collection_name="eval_pipeline",
        persist_directory=str(tmp_path_factory.mktemp("chroma")),
        embedding_function=LexicalEmbeddings(),
    )
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = []
    for path in sorted(UPLOADS.rglob("*.md")):
        docs.extend(
            rag_module.load_file(str(path), path.parent.name)
        )
    store.add_documents(splitter.split_documents(docs))
    return store


@pytest.fixture(scope="module")
def golden():
    return json.loads((ROOT / "eval" / "golden_set.json").read_text())["questions"]


def test_runner_scores_the_whole_golden_set(indexed_store, golden):
    from scripts.evaluate_retrieval import run_condition

    with patch.object(rag_module, "get_vectorstore", return_value=indexed_store):
        result = run_condition(golden, k=5, cohere_key=None, label="offline")

    assert result.n_questions == len(golden)
    assert 0.0 <= result.recall_at_k <= 1.0
    assert 0.0 <= result.mrr <= 1.0
    # MRR can never exceed recall@k: you cannot rank what you did not retrieve.
    assert result.mrr <= result.recall_at_k + 1e-9


def test_pipeline_actually_retrieves_relevant_documents(indexed_store, golden):
    """Sanity floor: with a genuinely lexical embedder, retrieval must beat
    nothing. This catches a pipeline that silently returns empty results."""
    from scripts.evaluate_retrieval import run_condition

    with patch.object(rag_module, "get_vectorstore", return_value=indexed_store):
        result = run_condition(golden, k=5, cohere_key=None, label="offline")

    assert result.recall_at_k > 0.0, "pipeline retrieved nothing relevant at all"


def test_role_scoping_holds_during_evaluation(indexed_store, golden):
    """The eval must respect the same pre-filter as production.

    A Finance question asked as Finance must never surface an HR or
    Engineering document.
    """
    from scripts.evaluate_retrieval import retrieved_sources

    with patch.object(rag_module, "get_vectorstore", return_value=indexed_store):
        sources = retrieved_sources(
            "What was the gross margin?", "Finance", k=5, cohere_key=None
        )

    forbidden = {"engineering_master_doc.md", "compliance_policy.md",
                 "marketing_report_q4_2024.md"}
    assert not (set(sources) & forbidden), sources


def test_higher_k_cannot_reduce_recall(indexed_store, golden):
    """Monotonicity: recall@k is non-decreasing in k. A failure here means the
    cutoff is applied in the wrong place."""
    from scripts.evaluate_retrieval import run_condition

    with patch.object(rag_module, "get_vectorstore", return_value=indexed_store):
        low = run_condition(golden, k=1, cohere_key=None, label="k1")
        high = run_condition(golden, k=5, cohere_key=None, label="k5")

    assert high.recall_at_k >= low.recall_at_k


def test_k_actually_changes_how_many_documents_come_back(indexed_store, golden):
    """--k must reach the retriever.

    It previously did not: the retriever always fetched config.RETRIEVAL_K and
    the runner sliced afterwards, so a larger k was silently a no-op.
    """
    from scripts.evaluate_retrieval import retrieved_sources

    with patch.object(rag_module, "get_vectorstore", return_value=indexed_store):
        few = retrieved_sources("What is the vacation policy?", "General", k=1, cohere_key=None)
        many = retrieved_sources("What is the vacation policy?", "General", k=6, cohere_key=None)

    assert len(few) == 1
    assert len(many) > len(few)
