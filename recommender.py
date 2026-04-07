"""
recommender.py
--------------
ONLINE pipeline — run per user query.

Given a user-supplied plan JSON, finds the top-K most similar plans from the
pre-built catalog index and generates a plain-English explanation for each match.

Hybrid similarity score:
    score = STRUCTURED_WEIGHT * cosine(struct_query, struct_catalog)
          + SEMANTIC_WEIGHT   * cosine(sem_query,    sem_catalog)

CLI usage:
    python recommender.py path/to/my_plan.json
    python recommender.py path/to/my_plan.json --top-k 3 --no-explain

Programmatic usage:
    from recommender import recommend
    results = recommend(plan_dict)
"""
import argparse
import json
import logging
import os
import pickle

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    CATALOG_INDEX_DIR,
    EMBEDDING_MODEL,
    SEMANTIC_WEIGHT,
    STRUCTURED_WEIGHT,
    TOP_K,
)
from llm_client import call_model
from vectorizer import extract_features, plan_to_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Catalog loaded once and cached in memory ──────────────────────────────────
_catalog: dict | None = None
_embedder: SentenceTransformer | None = None


def _load_catalog() -> dict:
    global _catalog
    if _catalog is not None:
        return _catalog

    required = [
        "catalog_structured.npy",
        "catalog_semantic.npy",
        "plan_metadata.json",
        "scaler.pkl",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(CATALOG_INDEX_DIR, f))]
    if missing:
        raise FileNotFoundError(
            f"Catalog index incomplete — missing: {missing}. "
            "Run `python catalog_builder.py` first."
        )

    _catalog = {
        "structured": np.load(os.path.join(CATALOG_INDEX_DIR, "catalog_structured.npy")),
        "semantic":   np.load(os.path.join(CATALOG_INDEX_DIR, "catalog_semantic.npy")),
        "metadata":   json.load(open(os.path.join(CATALOG_INDEX_DIR, "plan_metadata.json"))),
        "scaler":     pickle.load(open(os.path.join(CATALOG_INDEX_DIR, "scaler.pkl"), "rb")),
    }
    logging.info(f"Catalog loaded: {len(_catalog['metadata'])} plans.")
    return _catalog


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logging.info(f"Loading embedding model: {EMBEDDING_MODEL!r} …")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


# ── Explanation ───────────────────────────────────────────────────────────────

def _explain(query_plan: dict, catalog_plan: dict) -> str:
    """
    Ask Phi-3/Ollama to explain in plain English why the catalog plan was matched.
    Returns the model reply, or a fallback message if the model is unavailable.
    """
    query_summary   = plan_to_text(query_plan)
    catalog_summary = plan_to_text(catalog_plan)

    prompt = (
        "You are a health insurance expert helping a member understand plan options.\n\n"
        "A member's current plan and a similar catalog plan are shown below. "
        "In 2–3 sentences, explain the key reasons this catalog plan was matched. "
        "Focus on the most important similarities in cost-sharing structure, "
        "network type, and coverage benefits. Be specific and concise.\n\n"
        f"MEMBER'S PLAN:\n{query_summary}\n\n"
        f"MATCHED CATALOG PLAN:\n{catalog_summary}"
    )

    return call_model([{"role": "user", "content": prompt}], max_new_tokens=256)


# ── Core recommendation function ──────────────────────────────────────────────

def recommend(
    query_plan: dict,
    top_k: int = TOP_K,
    explain: bool = True,
) -> list[dict]:
    """
    Find the top-k catalog plans most similar to a query plan.

    Args:
        query_plan: Parsed plan JSON dict (the user's current plan).
        top_k:      Number of results to return.
        explain:    If True, call the LLM to generate a plain-English explanation
                    for each match. Set to False for faster, score-only results.

    Returns:
        List of result dicts ordered by similarity (highest first), each containing:
            rank             — 1-based position
            plan_name        — display name from plan_details
            insurer          — insurer name
            plan_type        — HMO / PPO / etc.
            metal_level      — Bronze / Silver / Gold / Platinum
            network_name     — network name
            similarity_score — hybrid weighted score (0–1)
            structured_score — cosine similarity on scaled numeric features
            semantic_score   — cosine similarity on sentence embeddings
            file_path        — path to the catalog JSON
            explanation      — plain-English match rationale (or "" if explain=False)
    """
    catalog  = _load_catalog()
    embedder = _get_embedder()

    n_catalog = len(catalog["metadata"])
    k = min(top_k, n_catalog)

    # ── Vectorize query ───────────────────────────────────────────────────────
    query_struct   = extract_features(query_plan).reshape(1, -1)
    query_struct_s = catalog["scaler"].transform(query_struct)        # (1, F)

    query_text    = plan_to_text(query_plan)
    query_sem     = embedder.encode([query_text])                     # (1, D)

    # ── Similarity ────────────────────────────────────────────────────────────
    struct_sims = cosine_similarity(query_struct_s, catalog["structured"])[0]  # (N,)
    sem_sims    = cosine_similarity(query_sem,      catalog["semantic"])[0]    # (N,)

    hybrid_sims = STRUCTURED_WEIGHT * struct_sims + SEMANTIC_WEIGHT * sem_sims  # (N,)

    top_indices = np.argsort(hybrid_sims)[::-1][:k]

    # ── Build results ─────────────────────────────────────────────────────────
    results = []
    for rank, idx in enumerate(top_indices, 1):
        meta = catalog["metadata"][idx]

        if explain:
            with open(meta["file_path"], encoding="utf-8") as f:
                catalog_plan = json.load(f)
            explanation = _explain(query_plan, catalog_plan)
        else:
            explanation = ""

        results.append({
            "rank":             rank,
            "plan_name":        meta["plan_name"],
            "insurer":          meta["insurer"],
            "plan_type":        meta["plan_type"],
            "metal_level":      meta["metal_level"],
            "network_name":     meta["network_name"],
            "similarity_score": round(float(hybrid_sims[idx]), 4),
            "structured_score": round(float(struct_sims[idx]),  4),
            "semantic_score":   round(float(sem_sims[idx]),     4),
            "file_path":        meta["file_path"],
            "explanation":      explanation,
        })

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_results(results: list[dict], query_name: str) -> None:
    width = 72
    print("\n" + "=" * width)
    print(f"  Top {len(results)} matches for: {query_name}")
    print("=" * width)

    for r in results:
        print(f"\n  #{r['rank']}  {r['plan_name']}")
        print(f"       Insurer : {r['insurer']}")
        print(f"       Type    : {r['plan_type']}  |  Metal: {r['metal_level']}  |  Network: {r['network_name']}")
        print(
            f"       Score   : {r['similarity_score']:.4f}  "
            f"(structured {r['structured_score']:.4f}  |  semantic {r['semantic_score']:.4f})"
        )
        if r["explanation"]:
            print(f"\n       Why matched:")
            for line in r["explanation"].strip().splitlines():
                print(f"         {line}")
        print()

    print("=" * width + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find health insurance plans similar to a given plan JSON."
    )
    parser.add_argument(
        "query",
        help="Path to the query plan JSON file.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help=f"Number of results to return (default: {TOP_K}).",
    )
    parser.add_argument(
        "--no-explain",
        action="store_true",
        help="Skip LLM explanation (faster; returns scores only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of formatted text.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.query):
        parser.error(f"Query file not found: {args.query!r}")

    with open(args.query, encoding="utf-8") as f:
        query_plan = json.load(f)

    query_name = (
        query_plan.get("plan_details", {}).get("plan_name")
        or os.path.basename(args.query)
    )

    logging.info(f"Query plan: {query_name!r}")

    results = recommend(query_plan, top_k=args.top_k, explain=not args.no_explain)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        _print_results(results, query_name)


if __name__ == "__main__":
    main()
