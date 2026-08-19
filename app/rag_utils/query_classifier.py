"""Routes a question to either the SQL path or the document-retrieval path."""

from functools import lru_cache

from openai import OpenAI

from .. import config

_client = None


def _get_client() -> OpenAI:
    # Built on first use so importing this module does not require a key.
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.require_openai_key())
    return _client


PROMPT = """\
You are a classifier that decides if a user's question should be handled by structured SQL query logic or by unstructured document search (RAG).

If the question involves structured data analysis (e.g. "average", "sum", "total", "count", "how many", "filter", "greater than", "less than", "top 5", "group by", "details of employee"), classify it as:

-> "SQL"

If the question is about general understanding, summarization, definitions, policies or processes, or cannot be answered from tabular data, classify it as:

-> "RAG"

Respond with only one word: either SQL or RAG.

Question: "{question}"

Answer:"""


@lru_cache(maxsize=128)
def detect_query_type_llm(question: str) -> str:
    """Return "SQL" or "RAG". Falls back to RAG if the call fails."""
    try:
        response = _get_client().chat.completions.create(
            model=config.CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": PROMPT.format(question=question)}],
            temperature=0,
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().upper()
        return "SQL" if "SQL" in answer else "RAG"
    except config.MissingCredentialError:
        raise
    except Exception as exc:
        # A classifier failure should not take the request down; document
        # retrieval is the safer default.
        print(f"[classifier] falling back to RAG: {exc}")
        return "RAG"
