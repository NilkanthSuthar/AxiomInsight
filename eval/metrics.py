"""Retrieval metrics.

Kept separate from the runner so the arithmetic can be tested without an API
key or an index.
"""

from dataclasses import dataclass


def first_relevant_rank(retrieved_sources: list[str], relevant_source: str) -> int | None:
    """1-based rank of the first relevant document, or None if absent."""
    for rank, source in enumerate(retrieved_sources, start=1):
        if source == relevant_source:
            return rank
    return None


def recall_at_k(retrieved_sources: list[str], relevant_source: str, k: int) -> float:
    """Fraction of relevant documents found in the top k.

    This golden set has exactly one relevant document per question, so this is
    1.0 or 0.0 per question, and its mean is the hit rate at k.
    """
    rank = first_relevant_rank(retrieved_sources[:k], relevant_source)
    return 1.0 if rank is not None else 0.0


def reciprocal_rank(retrieved_sources: list[str], relevant_source: str) -> float:
    """1/rank of the first relevant document, or 0 if it was never retrieved."""
    rank = first_relevant_rank(retrieved_sources, relevant_source)
    return 1.0 / rank if rank else 0.0


@dataclass
class EvalResult:
    label: str
    k: int
    n_questions: int
    recall_at_k: float
    mrr: float
    misses: list[str]

    def as_row(self) -> str:
        return (
            f"{self.label:<24} {self.recall_at_k:>10.3f} {self.mrr:>10.3f} "
            f"{len(self.misses):>8d}"
        )


def evaluate(per_question: list[tuple[str, list[str], str]], k: int, label: str) -> EvalResult:
    """Score a set of (question, retrieved_sources, relevant_source) triples."""
    recalls, rrs, misses = [], [], []
    for question, retrieved, relevant in per_question:
        r = recall_at_k(retrieved, relevant, k)
        recalls.append(r)
        rrs.append(reciprocal_rank(retrieved[:k], relevant))
        if not r:
            misses.append(question)

    n = len(per_question) or 1
    return EvalResult(
        label=label,
        k=k,
        n_questions=len(per_question),
        recall_at_k=sum(recalls) / n,
        mrr=sum(rrs) / n,
        misses=misses,
    )
