"""Thin async wrapper over the retrieval chain."""

from .rag_module import get_rag_chain


async def ask_rag(question: str, role: str, cohere_api_key: str = None) -> dict:
    chain = get_rag_chain(user_role=role, cohere_api_key=cohere_api_key)
    # ainvoke, not invoke: the chain makes network calls, and calling the
    # synchronous version here blocked the event loop for their duration.
    result = await chain.ainvoke({"input": question})
    return {"answer": result["answer"]}
