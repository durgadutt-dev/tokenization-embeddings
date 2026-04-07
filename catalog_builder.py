"""
catalog_builder.py
------------------
OFFLINE pipeline — run once when the catalog is built or updated.

Reads all plan JSON files from CATALOG_DIR, extracts hybrid vectors
(structured numeric features + semantic embeddings), and saves the index
to CATALOG_INDEX_DIR so the recommender can load it instantly at query time.

Usage:
    python catalog_builder.py

Output (written to CATALOG_INDEX_DIR):
    catalog_structured.npy   — shape (N, NUM_FEATURES), StandardScaler-normalised
    catalog_semantic.npy     — shape (N, embedding_dim), raw sentence embeddings
    plan_metadata.json       — list of plan identifiers and display fields
    scaler.pkl               — fitted StandardScaler for normalising query vectors
"""
import glob
import json
import logging
import os
import pickle

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler

from config import CATALOG_DIR, CATALOG_INDEX_DIR, EMBEDDING_MODEL
from vectorizer import extract_features, plan_to_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)


def build_catalog() -> list[dict]:
    """
    Build the catalog index from all JSON files in CATALOG_DIR.

    Returns:
        List of plan metadata dicts (same as what is written to plan_metadata.json).
    """
    os.makedirs(CATALOG_INDEX_DIR, exist_ok=True)

    json_files = sorted(glob.glob(os.path.join(CATALOG_DIR, "*.json")))
    if not json_files:
        raise FileNotFoundError(
            f"No JSON files found in {CATALOG_DIR!r}. "
            "Add plan JSONs to the catalog directory and re-run."
        )

    logging.info(f"Found {len(json_files)} plan(s) in {CATALOG_DIR!r}.")

    plans = []
    for path in json_files:
        with open(path, encoding="utf-8") as f:
            plan = json.load(f)
        plans.append((path, plan))

    # ── Structured numeric features ───────────────────────────────────────────
    logging.info("Extracting structured features …")
    raw_features = np.stack([extract_features(p) for _, p in plans])  # (N, F)

    scaler = StandardScaler()
    structured_scaled = scaler.fit_transform(raw_features)             # (N, F)
    logging.info(f"Structured matrix: {structured_scaled.shape}")

    # ── Semantic embeddings ───────────────────────────────────────────────────
    logging.info(f"Loading embedding model: {EMBEDDING_MODEL!r} …")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    texts = [plan_to_text(p) for _, p in plans]
    logging.info("Encoding plan texts …")
    semantic = embedder.encode(texts, show_progress_bar=True, batch_size=32)  # (N, D)
    logging.info(f"Semantic matrix: {semantic.shape}")

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = []
    for path, plan in plans:
        pd_ = plan.get("plan_details", {})
        metadata.append({
            "file_path":   path,
            "plan_id":     pd_.get("plan_id",     os.path.splitext(os.path.basename(path))[0]),
            "plan_name":   pd_.get("plan_name",   os.path.basename(path)),
            "insurer":     pd_.get("insurer",     "Unknown"),
            "plan_type":   pd_.get("plan_type",   "Unknown"),
            "metal_level": pd_.get("metal_level", "Unknown"),
            "network_name":pd_.get("network_name","Unknown"),
        })

    # ── Persist ───────────────────────────────────────────────────────────────
    np.save(os.path.join(CATALOG_INDEX_DIR, "catalog_structured.npy"), structured_scaled)
    np.save(os.path.join(CATALOG_INDEX_DIR, "catalog_semantic.npy"),   semantic)

    with open(os.path.join(CATALOG_INDEX_DIR, "plan_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with open(os.path.join(CATALOG_INDEX_DIR, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    logging.info(f"Catalog index saved to {CATALOG_INDEX_DIR!r}.")
    for m in metadata:
        logging.info(f"  ✓ {m['plan_name']}")

    return metadata


if __name__ == "__main__":
    build_catalog()
