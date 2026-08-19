"""The retrieval metrics, checked against hand-computed values."""

import json
import pathlib

import pytest

from eval.metrics import evaluate, first_relevant_rank, recall_at_k, reciprocal_rank


# --- rank ------------------------------------------------------------------
def test_rank_is_one_based():
    assert first_relevant_rank(["a.md", "b.md"], "a.md") == 1
    assert first_relevant_rank(["a.md", "b.md"], "b.md") == 2


def test_rank_is_none_when_absent():
    assert first_relevant_rank(["a.md"], "z.md") is None


def test_rank_finds_first_occurrence():
    assert first_relevant_rank(["x.md", "a.md", "a.md"], "a.md") == 2


# --- recall@k --------------------------------------------------------------
@pytest.mark.parametrize(
    "retrieved,k,expected",
    [
        (["a.md", "b.md", "c.md"], 1, 1.0),   # relevant is rank 1
        (["b.md", "a.md", "c.md"], 1, 0.0),   # rank 2, outside k=1
        (["b.md", "a.md", "c.md"], 2, 1.0),   # rank 2, inside k=2
        (["b.md", "c.md", "a.md"], 2, 0.0),   # rank 3, outside k=2
        ([], 3, 0.0),                          # nothing retrieved
    ],
)
def test_recall_at_k_respects_the_cutoff(retrieved, k, expected):
    assert recall_at_k(retrieved, "a.md", k) == expected


# --- MRR -------------------------------------------------------------------
@pytest.mark.parametrize(
    "retrieved,expected",
    [
        (["a.md", "b.md"], 1.0),
        (["b.md", "a.md"], 0.5),
        (["b.md", "c.md", "a.md"], pytest.approx(1 / 3)),
        (["x.md"], 0.0),
    ],
)
def test_reciprocal_rank(retrieved, expected):
    assert reciprocal_rank(retrieved, "a.md") == expected


# --- aggregate -------------------------------------------------------------
def test_evaluate_averages_across_questions():
    per_question = [
        ("q1", ["a.md", "z.md"], "a.md"),   # rank 1 -> recall 1, rr 1.0
        ("q2", ["z.md", "b.md"], "b.md"),   # rank 2 -> recall 1, rr 0.5
        ("q3", ["z.md", "y.md"], "c.md"),   # miss   -> recall 0, rr 0.0
    ]
    result = evaluate(per_question, k=3, label="test")
    assert result.n_questions == 3
    assert result.recall_at_k == pytest.approx(2 / 3)
    assert result.mrr == pytest.approx((1.0 + 0.5 + 0.0) / 3)
    assert result.misses == ["q3"]


def test_evaluate_on_empty_set_does_not_divide_by_zero():
    result = evaluate([], k=3, label="empty")
    assert result.recall_at_k == 0.0 and result.mrr == 0.0


def test_perfect_and_zero_retrieval_are_the_bounds():
    perfect = evaluate([("q", ["a.md"], "a.md")], k=1, label="p")
    nothing = evaluate([("q", ["z.md"], "a.md")], k=1, label="z")
    assert perfect.recall_at_k == 1.0 and perfect.mrr == 1.0
    assert nothing.recall_at_k == 0.0 and nothing.mrr == 0.0


# --- golden set integrity --------------------------------------------------
GOLDEN = json.loads(
    (pathlib.Path(__file__).parent.parent / "eval" / "golden_set.json").read_text()
)
UPLOADS = pathlib.Path(__file__).parent.parent / "static" / "uploads"


def test_golden_set_is_not_empty():
    assert len(GOLDEN["questions"]) >= 20


def test_every_golden_answer_points_at_a_file_that_exists():
    available = {p.name for p in UPLOADS.rglob("*.md")}
    for item in GOLDEN["questions"]:
        assert item["relevant_source"] in available, item


def test_every_golden_source_is_readable_by_the_stated_role():
    """A question must be answerable by the role it is asked as.

    Otherwise the pre-filter would correctly exclude the answer and the
    evaluation would be measuring the wrong thing.
    """
    owner = {p.name: p.parent.name.lower() for p in UPLOADS.rglob("*.md")}
    for item in GOLDEN["questions"]:
        doc_role = owner[item["relevant_source"]]
        asked_as = item["role"].lower()
        assert doc_role in (asked_as, "general"), item


def test_golden_questions_are_unique():
    questions = [q["question"] for q in GOLDEN["questions"]]
    assert len(questions) == len(set(questions))
