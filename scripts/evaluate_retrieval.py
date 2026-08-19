"""Measure retrieval quality with and without Cohere reranking.

    python -m scripts.evaluate_retrieval
    python -m scripts.evaluate_retrieval --k 5 --json results.json

Requires an indexed vector store (run `python -m scripts.seed` first) and
OPENAI_API_KEY. Reranking is only measured when COHERE_API_KEY is also set;
without it the script reports the baseline alone and says so.

Whatever numbers this prints are the numbers. Nothing here targets a figure.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.rag_utils import rag_module  # noqa: E402
from eval.metrics import evaluate  # noqa: E402

GOLDEN_SET = Path(__file__).resolve().parent.parent / "eval" / "golden_set.json"


def retrieved_sources(question: str, role: str, k: int, cohere_key: str | None) -> list[str]:
    """Source filenames returned for one question, best first."""
    retriever = rag_module.get_retriever(role, cohere_api_key=cohere_key, k=k)
    docs = retriever.invoke(question)
    return [d.metadata.get("source", "?") for d in docs][:k]


def run_condition(questions, k: int, cohere_key: str | None, label: str):
    per_question = []
    for item in questions:
        sources = retrieved_sources(item["question"], item["role"], k, cohere_key)
        per_question.append((item["question"], sources, item["relevant_source"]))
    return evaluate(per_question, k=k, label=label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=config.RETRIEVAL_K,
                        help=f"documents to score (default {config.RETRIEVAL_K})")
    parser.add_argument("--json", metavar="PATH", help="also write results as JSON")
    parser.add_argument("--show-misses", action="store_true",
                        help="list questions whose answer was not retrieved")
    args = parser.parse_args()

    if not config.OPENAI_API_KEY:
        print("OPENAI_API_KEY is not set. Embeddings are needed to query the index.")
        return 1

    golden = json.loads(GOLDEN_SET.read_text())
    questions = golden["questions"]

    # An empty index would score 0.0 everywhere and look like a retrieval
    # failure rather than a missing setup step.
    store = rag_module.get_vectorstore()
    try:
        count = len(store.get()["documents"])
        if count == 0:
            print("The vector store is empty. Run `python -m scripts.seed` first.")
            return 1
        print(f"Index contains {count} chunks.")
    except Exception:
        pass  # not all backends expose a count; carry on

    print(f"Evaluating {len(questions)} questions at k={args.k}, "
          f"store={rag_module.get_backend().name}\n")

    results = [run_condition(questions, args.k, None, "vector only")]
    if config.COHERE_API_KEY:
        results.append(
            run_condition(questions, args.k, config.COHERE_API_KEY, "+ Cohere rerank")
        )
    else:
        print("COHERE_API_KEY is not set, so the rerank condition was skipped.\n")

    header = f"{'condition':<24} {f'recall@{args.k}':>10} {'MRR':>10} {'misses':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(r.as_row())

    if len(results) == 2:
        base, reranked = results
        d_recall = reranked.recall_at_k - base.recall_at_k
        d_mrr = reranked.mrr - base.mrr
        print(f"\nrerank delta: recall@{args.k} {d_recall:+.3f}, MRR {d_mrr:+.3f}")
        if base.mrr:
            print(f"              MRR relative change {(d_mrr / base.mrr) * 100:+.1f}%")

    if args.show_misses:
        for r in results:
            if r.misses:
                print(f"\nnot retrieved under '{r.label}':")
                for q in r.misses:
                    print(f"  - {q}")

    if args.json:
        payload = {
            "k": args.k,
            "n_questions": len(questions),
            "vector_store": rag_module.get_backend().name,
            "embedding_model": config.EMBEDDING_MODEL,
            "conditions": [
                {"label": r.label, "recall_at_k": r.recall_at_k, "mrr": r.mrr,
                 "misses": r.misses}
                for r in results
            ],
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nWrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
