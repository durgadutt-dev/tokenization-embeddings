"""
embedder.py
-----------
Chunks insurance document pages and stores embeddings in ChromaDB.

Each meaningful section of the document becomes a separate chunk so that
semantic search can pinpoint exactly which part of the plan answers a query.

Usage:
    from embedder import load_embedder, get_collection, embed_and_store

    embedder   = load_embedder()
    collection = get_collection()
    n_chunks   = embed_and_store(pages, plan_name, embedder, collection)
"""
import logging
import chromadb
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, CHROMA_DB_PATH


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def load_embedder() -> SentenceTransformer:
    """
    Load the sentence-transformers embedding model.

    The model is downloaded on first use (~80MB for all-MiniLM-L6-v2)
    and cached locally. Subsequent loads are instant.
    """
    logging.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    return SentenceTransformer(EMBEDDING_MODEL)


def get_collection(persist_path: str = CHROMA_DB_PATH):
    """
    Get or create the ChromaDB collection for insurance plans.

    Uses cosine similarity — appropriate for sentence embeddings where
    direction matters more than magnitude.

    The collection persists to disk so indexed plans survive app restarts.
    """
    client = chromadb.PersistentClient(path=persist_path)
    return client.get_or_create_collection(
        name="insurance_plans",
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_pages(pages: list[str], plan_name: str) -> list[dict]:
    """
    Split document pages into meaningful chunks for embedding.

    Strategy:
    - Table rows (pipe-separated) → one chunk per row.
      Each row captures a specific service with its network/OON cost.
    - Paragraphs → grouped into ~200 character chunks.
      Captures narrative sections like exclusions, rights, etc.

    Each chunk carries metadata so retrieval results can reference
    which plan and page the information came from.

    Args:
        pages:     List of page text strings from pdf_extractor.extract_pdf().
        plan_name: Human-readable plan identifier (usually the filename).

    Returns:
        List of chunk dicts with keys: id, text, metadata.
    """
    chunks = []
    chunk_id = 0

    for page_num, page_text in enumerate(pages):
        if not page_text.strip():
            continue

        sections = [s.strip() for s in page_text.split('\n\n') if s.strip()]

        for section in sections:
            if '[TABLE DATA]' in section:
                # Each pipe-separated table row → individual chunk
                lines = section.replace('[TABLE DATA]', '').strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # Only keep rows with actual content (skip header/empty rows)
                    if len(line) > 30 and '|' in line:
                        chunks.append({
                            "id": f"{plan_name}_{chunk_id}",
                            "text": line,
                            "metadata": {
                                "plan_name": plan_name,
                                "page_num": page_num + 1,
                                "type": "table_row",
                            },
                        })
                        chunk_id += 1
            else:
                # Group plain-text lines into ~200 char chunks
                current: list[str] = []
                for line in section.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    current.append(line)
                    if len(' '.join(current)) >= 200:
                        text = ' '.join(current)
                        chunks.append({
                            "id": f"{plan_name}_{chunk_id}",
                            "text": text,
                            "metadata": {
                                "plan_name": plan_name,
                                "page_num": page_num + 1,
                                "type": "text",
                            },
                        })
                        chunk_id += 1
                        current = []

                # Flush any remaining lines
                if current:
                    text = ' '.join(current)
                    if len(text) > 30:
                        chunks.append({
                            "id": f"{plan_name}_{chunk_id}",
                            "text": text,
                            "metadata": {
                                "plan_name": plan_name,
                                "page_num": page_num + 1,
                                "type": "text",
                            },
                        })
                        chunk_id += 1

    logging.info(f"Created {len(chunks)} chunks for plan: {plan_name}")
    return chunks


# ---------------------------------------------------------------------------
# Embed and store
# ---------------------------------------------------------------------------

def embed_and_store(
    pages: list[str],
    plan_name: str,
    embedder: SentenceTransformer,
    collection,
) -> int:
    """
    Chunk a document, embed all chunks, and store them in ChromaDB.

    Re-uploading the same plan_name replaces existing data cleanly —
    old chunks are deleted before new ones are inserted.

    Args:
        pages:     List of page text strings from pdf_extractor.extract_pdf().
        plan_name: Identifier for this plan (used for filtering in retrieval).
        embedder:  Loaded SentenceTransformer instance.
        collection: ChromaDB collection to store into.

    Returns:
        Number of chunks stored.
    """
    # Remove stale entries for this plan before re-indexing
    existing = collection.get(where={"plan_name": plan_name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logging.info(f"Removed {len(existing['ids'])} stale chunks for: {plan_name}")

    chunks = _chunk_pages(pages, plan_name)
    if not chunks:
        logging.warning(f"No chunks generated for plan: {plan_name}")
        return 0

    texts     = [c["text"]     for c in chunks]
    ids       = [c["id"]       for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Encode all chunks in one batch — faster than one-by-one on MPS/CPU
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    logging.info(f"Stored {len(chunks)} chunks for plan: {plan_name}")
    return len(chunks)


def list_plans(collection) -> list[str]:
    """
    Return the names of all plans currently indexed in the collection.

    Used by the UI to show which plans are available for querying.
    """
    results = collection.get(include=["metadatas"])
    names = {m["plan_name"] for m in results["metadatas"]} if results["metadatas"] else set()
    return sorted(names)
