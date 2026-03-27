"""
retriever.py
------------
Semantic search over the ChromaDB insurance plan vector store.

At query time, the user's question is embedded and compared against
all stored chunks. The top-K most relevant chunks are returned as
context for the LLM to answer from.

Usage:
    from retriever import retrieve

    chunks = retrieve(question, collection, embedder)
    # pass chunks to llm_client.call_model() as context
"""
import logging
from sentence_transformers import SentenceTransformer
from config import RAG_TOP_K


def retrieve(
    question: str,
    collection,
    embedder: SentenceTransformer,
    top_k: int = RAG_TOP_K,
    plan_name: str | None = None,
) -> list[str]:
    """
    Find the most semantically relevant chunks for a user's question.

    Args:
        question:   The user's natural language query.
        collection: ChromaDB collection to search.
        embedder:   Loaded SentenceTransformer instance.
        top_k:      Number of chunks to return. Controlled by RAG_TOP_K in config.
        plan_name:  If provided, restricts search to chunks from this plan only.
                    If None, searches across all indexed plans.

    Returns:
        List of chunk text strings ordered by relevance (most relevant first).
        Returns empty list if the collection has no documents.
    """
    # Guard: collection must have documents to query
    if collection.count() == 0:
        logging.warning("retrieve: collection is empty — no plans indexed yet.")
        return []

    query_embedding = embedder.encode(question).tolist()

    # Optionally filter to a specific plan
    where = {"plan_name": plan_name} if plan_name else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),  # can't request more than available
        where=where,
        include=["documents", "metadatas"],
    )

    chunks = results["documents"][0] if results["documents"] else []

    logging.info(
        f"Retrieved {len(chunks)} chunks for query: '{question[:60]}'"
        + (f" | plan filter: {plan_name}" if plan_name else "")
    )
    return chunks
