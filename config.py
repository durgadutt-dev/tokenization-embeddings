import torch

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL_ID = "microsoft/Phi-3-mini-128k-instruct"

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"

DEVICE = get_device()

# ── LLM generation ────────────────────────────────────────────────────────────
MAX_NEW_TOKENS = 512    # token budget for chat responses
TEMPERATURE    = 0.7
DO_SAMPLE      = True

# ── Backend ───────────────────────────────────────────────────────────────────
BACKEND     = "ollama"
OLLAMA_MODEL = "phi3:mini"

# ── RAG ───────────────────────────────────────────────────────────────────────
# Embedding model — runs fully locally via sentence-transformers.
# all-MiniLM-L6-v2 is fast (~80MB), MPS-accelerated, and good enough for
# insurance domain retrieval.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Directory where ChromaDB persists its vector index to disk.
CHROMA_DB_PATH = "./chroma_db"

# Number of chunks to retrieve per query.
# 5 gives the LLM enough context without overloading the prompt.
RAG_TOP_K = 5
